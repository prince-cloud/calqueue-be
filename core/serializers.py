from rest_framework import serializers
from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
)


class GetTicketSerializer(serializers.Serializer):
    device = serializers.UUIDField()
    # get the branch from the device
    customer_phone_number = serializers.CharField()
    id_number = serializers.CharField()
    id_type = serializers.CharField()
    services = serializers.ListField(child=serializers.JSONField())


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
