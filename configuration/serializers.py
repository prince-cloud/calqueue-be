from rest_framework import serializers
from django.core.cache import cache
from django.utils import timezone
from helpers import exceptions
from .models import Branch, BranchWorkingHours, Device, MainService, Service, Counter, SystemVoiceConfig, BranchVoiceConfig, BranchTVConfig, TVAdvertisement, OtherBank, OtherBankBranch


class BranchWorkingHoursSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source="get_day_display", read_only=True)

    class Meta:
        model = BranchWorkingHours
        fields = ("day", "day_name", "open_time", "close_time", "is_closed")


class BranchSerializer(serializers.ModelSerializer):
    working_hours = BranchWorkingHoursSerializer(many=True, read_only=True)

    class Meta:
        model = Branch
        fields = (
            "uuid",
            "name",
            "code",
            "location",
            "latitude",
            "longitude",
            "working_hours",
        )


class NearestBranchSerializer(BranchSerializer):
    """Branch payload for the mobile check-in flow, with computed distance.
    Expects ``distance_km`` / ``distance_m`` attached to each instance."""

    distance_km = serializers.FloatField(read_only=True)
    distance_m = serializers.FloatField(read_only=True)

    class Meta(BranchSerializer.Meta):
        fields = BranchSerializer.Meta.fields + ("distance_km", "distance_m")


class DeviceSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = Device
        fields = (
            "uuid",
            "username",
            "device_id",
            "serial_number",
            "label",
            "branch",
            "last_login",
        )


class BranchWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ("name", "code", "location", "latitude", "longitude", "is_active")


class DeviceWriteSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(
        slug_field="uuid", queryset=Branch.objects.all()
    )
    password = serializers.CharField(required=False)

    class Meta:
        model = Device
        fields = ("username", "password", "serial_number", "label", "branch", "is_active")

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class DeviceLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs["username"]
        password = attrs["password"]

        attempt_key = f"device-login-attempt/{username}"
        attempt = cache.get(attempt_key, 0) + 1
        cache.set(attempt_key, attempt, 60 * 5)
        if attempt > 5:
            raise exceptions.TooManyLoginAttemptsException()

        try:
            device = Device.objects.select_related("branch").get(
                username=username, is_active=True
            )
        except Device.DoesNotExist:
            raise exceptions.LoginException()

        if not device.check_password(password):
            raise exceptions.LoginException()

        cache.delete(attempt_key)
        device.last_login = timezone.now()
        device.save(update_fields=["last_login"])

        attrs["device"] = device
        return attrs


class DeviceRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("uuid", "name", "prefix", "icon", "description", "is_active")


class ServiceWriteSerializer(serializers.ModelSerializer):
    main_service = serializers.SlugRelatedField(
        slug_field="uuid", queryset=MainService.objects.all()
    )

    class Meta:
        model = Service
        fields = ("name", "prefix", "main_service", "icon", "description", "is_active")


class MainServiceSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = MainService
        fields = ("uuid", "name", "icon", "description", "is_active", "services")


class CounterSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)
    operations = ServiceSerializer(many=True, read_only=True)
    current_ticket_number = serializers.CharField(
        source="current_ticket.ticket_number", read_only=True, default=None
    )

    class Meta:
        model = Counter
        fields = (
            "uuid",
            "branch",
            "counter_code",
            "counter_name",
            "counter_type",
            "is_active",
            "is_backoffice",
            "operations",
            "current_ticket",
            "current_ticket_number",
        )


class CounterWriteSerializer(serializers.ModelSerializer):
    branch = serializers.SlugRelatedField(slug_field="uuid", queryset=Branch.objects.all())
    operations = serializers.SlugRelatedField(
        slug_field="uuid", queryset=Service.objects.filter(is_active=True), many=True, required=False
    )

    class Meta:
        model = Counter
        fields = (
            "branch",
            "counter_code",
            "counter_name",
            "counter_type",
            "is_active",
            "is_backoffice",
            "operations",
        )

    def create(self, validated_data):
        operations = validated_data.pop("operations", [])
        instance = Counter.objects.create(**validated_data)
        instance.operations.set(operations)
        return instance

    def update(self, instance, validated_data):
        operations = validated_data.pop("operations", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if operations is not None:
            instance.operations.set(operations)
        return instance


class SystemVoiceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemVoiceConfig
        fields = ("engine", "voice", "rate", "language", "tld", "slow", "announcement_template", "updated_at")
        read_only_fields = ("updated_at",)


class BranchVoiceConfigSerializer(serializers.ModelSerializer):
    branch_uuid = serializers.UUIDField(source="branch.uuid", read_only=True)

    class Meta:
        model = BranchVoiceConfig
        fields = ("branch_uuid", "engine", "voice", "rate", "language", "tld", "slow", "announcement_template", "updated_at")
        read_only_fields = ("branch_uuid", "updated_at")


class TVAdvertisementSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TVAdvertisement
        fields = ("id", "media_type", "file_url", "order", "created_at")
        read_only_fields = ("id", "file_url", "created_at")

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class TVAdvertisementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TVAdvertisement
        fields = ("media_type", "file", "order")


class OtherBankBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherBankBranch
        fields = ("uuid", "name", "code", "is_active")


class OtherBankSerializer(serializers.ModelSerializer):
    branches = OtherBankBranchSerializer(many=True, read_only=True)

    class Meta:
        model = OtherBank
        fields = ("uuid", "name", "code", "is_active", "branches")


class OtherBankWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherBank
        fields = ("name", "code", "is_active")


class OtherBankBranchWriteSerializer(serializers.ModelSerializer):
    bank = serializers.SlugRelatedField(slug_field="uuid", queryset=OtherBank.objects.all())
    code = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = OtherBankBranch
        fields = ("bank", "name", "code", "is_active")


class BranchTVConfigSerializer(serializers.ModelSerializer):
    branch_uuid = serializers.UUIDField(source="branch.uuid", read_only=True)
    advertisements = serializers.SerializerMethodField()

    class Meta:
        model = BranchTVConfig
        fields = ("branch_uuid", "ticker_texts", "show_ads", "advertisements", "updated_at")
        read_only_fields = ("branch_uuid", "advertisements", "updated_at")

    def get_advertisements(self, obj):
        ads = obj.advertisements.all()
        return TVAdvertisementSerializer(ads, many=True, context=self.context).data
