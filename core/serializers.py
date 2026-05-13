import json
from rest_framework import serializers
from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
)
from configuration.models import Device
from helpers import exceptions


class GetTicketSerializer(serializers.Serializer):
    device = serializers.UUIDField()
    # get the branch from the device
    phone_number = serializers.CharField()
    id_number = serializers.CharField()
    id_type = serializers.CharField()
    signature = serializers.FileField(allow_null=True, required=False)
    services = serializers.JSONField()

    def validate_device(self, value):
        try:
            device = Device.objects.get(uuid=value)
        except Device.DoesNotExist:
            raise exceptions.GeneralException(detail="Device not found.")
        return device

    def validate_services(self, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                raise exceptions.GeneralException(detail="Services must be valid JSON.")
        else:
            parsed = value

        if not isinstance(parsed, list):
            raise exceptions.GeneralException(
                detail="Services must be a JSON array of objects."
            )

        normalized = []
        for i, item in enumerate(parsed):
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except json.JSONDecodeError:
                    raise exceptions.GeneralException(
                        detail=f"Services[{i}] must be a valid JSON object."
                    )
            if not isinstance(item, dict):
                raise exceptions.GeneralException(
                    detail=f'Services[{i}] must be a JSON object (e.g. {{"id": …, "name": …}}).'
                )
            normalized.append(item)

        return normalized


class CashDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashDeposit
        fields = (
            "uuid",
            "deposit_type",
            "account_number",
            "account_name",
            "amount",
            "phone_number",
            "depositor_name",
            "residential_address",
            "occupation",
            "id_type",
            "nationality",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        deposit_type = attrs.get("deposit_type") or (
            self.instance.deposit_type if self.instance else None
        )
        if deposit_type == CashDeposit.DepositType.THIRD_PARTY:
            required = ["residential_address", "occupation", "id_type", "nationality"]
            errors = {
                f: "Required for third party deposits."
                for f in required
                if not attrs.get(f)
            }
            if errors:
                raise serializers.ValidationError(errors)
        return attrs


class ChequeDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChequeDeposit
        fields = (
            "uuid",
            "cheque_type",
            "beneficiary_account_number",
            "beneficiary_account_name",
            "cheque_details",
            "phone_number",
            "depositor_name",
            "created_at",
            "updated_at",
        )


class EZWICHDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = EZWICHDeposit
        fields = (
            "uuid",
            "id_type",
            "id_number",
            "ezwich_card_number",
            "amount",
            "name",
            "residential_address",
            "occupation",
            "phone_number",
            "created_at",
            "updated_at",
        )


class MobileMoneyDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileMoneyDeposit
        fields = (
            "uuid",
            "id_type",
            "id_number",
            "name",
            "residential_address",
            "phone_number",
            "amount",
            "occupation",
            "created_at",
            "updated_at",
        )
