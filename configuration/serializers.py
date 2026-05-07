from rest_framework import serializers
from django.core.cache import cache
from django.utils import timezone
from helpers import exceptions
from .models import Branch, BranchWorkingHours, Device, MainService, Service


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
        fields = ("uuid", "name", "icon", "description", "is_active")


class MainServiceSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = MainService
        fields = ("uuid", "name", "icon", "description", "is_active", "services")
