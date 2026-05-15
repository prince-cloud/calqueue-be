from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from configuration.models import Branch, Device, ServiceTypes
from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
    Ticket,
)

_VALID_SERVICE_TYPES = set(ServiceTypes.values)
_SERVICE_TYPE_LABELS = dict(
    ServiceTypes.choices
)  # {"CASH DEPOSIT": "Cash Deposit", ...}


def _next_ticket_number(branch, lead_service_type):
    prefix = (lead_service_type[0] if lead_service_type else "T").upper()
    today = timezone.now().date()
    count = Ticket.objects.filter(branch=branch, created_at__date=today).count() + 1
    return f"{prefix}{count:03d}"


# ---------------------------------------------------------------------------
# Polymorphic services write field
# ---------------------------------------------------------------------------


class _ServicesField(serializers.Field):
    """
    Accepts a list of service objects each with a service_type field.
    The rest of each object's data is stored as-is in services_data (JSON).
    No DB lookup required — service_type is validated against the ServiceTypes enum.
    """

    def to_internal_value(self, data):
        # Form-encoded requests send JSON fields as strings — parse them first
        if isinstance(data, str):
            import json
            try:
                data = json.loads(data)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Must be a valid JSON list.")

        if not isinstance(data, list) or not data:
            raise serializers.ValidationError("Must be a non-empty list.")

        validated_items = []
        item_errors = {}

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                item_errors[i] = {"non_field_errors": ["Expected an object."]}
                continue
            service_type = item.get("service_type")
            if service_type not in _VALID_SERVICE_TYPES:
                item_errors[i] = {
                    "service_type": [f"'{service_type}' is not a valid service type."]
                }
                continue
            validated_items.append(dict(item))

        if item_errors:
            raise serializers.ValidationError(item_errors)

        return validated_items

    def to_representation(self, value):
        return value


# ---------------------------------------------------------------------------
# Ticket — write
# ---------------------------------------------------------------------------


class TicketWriteSerializer(serializers.Serializer):
    device = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=20)
    id_number = serializers.CharField(max_length=50)
    id_type = serializers.CharField(max_length=50)
    signature = serializers.ImageField(required=False, allow_null=True)
    services = _ServicesField()

    def validate_device(self, value):
        try:
            return Device.objects.select_related("branch").get(
                uuid=value, is_active=True
            )
        except Device.DoesNotExist:
            raise serializers.ValidationError("Device not found or inactive.")

    def validate(self, attrs):
        device = attrs["device"]
        if not device.branch_id:
            raise serializers.ValidationError(
                {"device": "Device has no branch assigned."}
            )
        attrs["branch"] = device.branch
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        service_items = validated_data.pop("services")
        branch = validated_data.pop("branch")

        # Lock the branch row so concurrent ticket creations for the same
        # branch queue behind each other, preventing duplicate ticket numbers.
        branch = Branch.objects.select_for_update().get(pk=branch.pk)

        ticket = Ticket.objects.create(
            branch=branch,
            ticket_number=_next_ticket_number(branch, service_items[0]["service_type"]),
            services_data=service_items,
            **validated_data,
        )
        return ticket


# ---------------------------------------------------------------------------
# Ticket — read
# ---------------------------------------------------------------------------


class TicketSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    branch_code = serializers.CharField(source="branch.code", read_only=True)
    counter_name = serializers.CharField(
        source="counter.counter_name", read_only=True, default=None
    )
    served_by_name = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = (
            "uuid",
            "ticket_number",
            "reference_number",
            "branch_name",
            "branch_code",
            "phone_number",
            "id_number",
            "id_type",
            "status",
            "counter_name",
            "served_by_name",
            "services",
            "waiting_time",
            "called_time",
            "start_serve_time",
            "served_time",
            "total_time_spent",
            "created_at",
            "updated_at",
            "audio_url",
        )

    def get_served_by_name(self, obj):
        teller = obj.servced_by  # typo preserved from the model
        if not teller:
            return None
        return teller.get_full_name() or teller.email

    def get_services(self, obj):
        return [
            {
                **item,
                "service_name": _SERVICE_TYPE_LABELS.get(item.get("service_type"), ""),
                "position": i,
            }
            for i, item in enumerate(obj.services_data)
        ]

    def get_audio_url(self, obj):
        if not obj.ticket_audio:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.ticket_audio.url)
        return obj.ticket_audio.url


# ---------------------------------------------------------------------------
# Deposit serializers — writable ticket + served_by UUID fields
# ---------------------------------------------------------------------------

from accounts.models import CustomUser  # noqa: E402


class _DepositBaseSerializer(serializers.ModelSerializer):
    """Shared behaviour: ticket and served_by resolved by UUID."""
    ticket = serializers.SlugRelatedField(
        slug_field="uuid", queryset=Ticket.objects.all(), allow_null=True, required=False
    )
    served_by = serializers.SlugRelatedField(
        slug_field="uuid", queryset=CustomUser.objects.all(), allow_null=True, required=False
    )
    served_by_name = serializers.SerializerMethodField(read_only=True)

    def get_served_by_name(self, obj):
        if not obj.served_by_id:
            return None
        return obj.served_by.get_full_name() or obj.served_by.email


class CashDepositSerializer(_DepositBaseSerializer):
    class Meta:
        model = CashDeposit
        fields = "__all__"
        read_only_fields = ("uuid", "t24_reference", "t24_status", "t24_response", "created_at", "updated_at")

    def validate(self, attrs):
        if attrs.get("deposit_type") == CashDeposit.DepositType.THIRD_PARTY:
            required = ["residential_address", "occupation", "id_type", "nationality"]
            errors = {
                f: "Required for third party deposits."
                for f in required
                if not attrs.get(f)
            }
            if errors:
                raise serializers.ValidationError(errors)
        return attrs


class ChequeDepositSerializer(_DepositBaseSerializer):
    class Meta:
        model = ChequeDeposit
        fields = "__all__"
        read_only_fields = ("uuid", "t24_reference", "t24_status", "t24_response", "created_at", "updated_at")


class EZWICHDepositSerializer(_DepositBaseSerializer):
    class Meta:
        model = EZWICHDeposit
        fields = "__all__"
        read_only_fields = ("uuid", "t24_reference", "t24_status", "t24_response", "created_at", "updated_at")


class MobileMoneyDepositSerializer(_DepositBaseSerializer):
    class Meta:
        model = MobileMoneyDeposit
        fields = "__all__"
        read_only_fields = ("uuid", "t24_reference", "t24_status", "t24_response", "created_at", "updated_at")
