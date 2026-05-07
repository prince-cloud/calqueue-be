from rest_framework.viewsets import ModelViewSet

from .filters import (
    CashDepositFilter,
    ChequeDepositFilter,
    EZWICHDepositFilter,
    MobileMoneyDepositFilter,
)
from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
)
from .serializers import (
    CashDepositSerializer,
    ChequeDepositSerializer,
    EZWICHDepositSerializer,
    MobileMoneyDepositSerializer,
)


class BaseTicketViewSet(ModelViewSet):
    lookup_field = "uuid"
    ordering_fields = ("created_at", "status", "ticket_number")


class CashDepositViewSet(BaseTicketViewSet):
    queryset = CashDeposit.objects.all()
    serializer_class = CashDepositSerializer
    filterset_class = CashDepositFilter
    search_fields = (
        "ticket_number",
        "account_number",
        "depositor_name",
        "phone_number",
    )


class ChequeDepositViewSet(BaseTicketViewSet):
    queryset = ChequeDeposit.objects.all()
    serializer_class = ChequeDepositSerializer
    filterset_class = ChequeDepositFilter
    search_fields = (
        "ticket_number",
        "beneficiary_account_number",
        "depositor_name",
        "phone_number",
    )


class EZWICHDepositViewSet(BaseTicketViewSet):
    queryset = EZWICHDeposit.objects.all()
    serializer_class = EZWICHDepositSerializer
    filterset_class = EZWICHDepositFilter
    search_fields = ("ticket_number", "ezwich_card_number", "name", "phone_number")


class MobileMoneyDepositViewSet(BaseTicketViewSet):
    queryset = MobileMoneyDeposit.objects.all()
    serializer_class = MobileMoneyDepositSerializer
    filterset_class = MobileMoneyDepositFilter
    search_fields = ("ticket_number", "name", "phone_number")
