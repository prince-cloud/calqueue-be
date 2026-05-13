from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework import status
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
    GetTicketSerializer,
)


class GetTicketViewset(APIView):
    serializer_class = GetTicketSerializer
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: create Ticket + TicketService rows + deposit payloads from serializer
        return Response(
            data={"status": True, "data": serializer.validated_data},
            status=status.HTTP_200_OK,
        )


class BaseTicketViewSet(ModelViewSet):
    lookup_field = "uuid"
    ordering_fields = ("created_at",)


class CashDepositViewSet(BaseTicketViewSet):
    queryset = CashDeposit.objects.all()
    serializer_class = CashDepositSerializer
    filterset_class = CashDepositFilter
    search_fields = (
        "ticket__ticket_number",
        "account_number",
        "depositor_name",
        "phone_number",
    )


class ChequeDepositViewSet(BaseTicketViewSet):
    queryset = ChequeDeposit.objects.all()
    serializer_class = ChequeDepositSerializer
    filterset_class = ChequeDepositFilter
    search_fields = (
        "ticket__ticket_number",
        "beneficiary_account_number",
        "depositor_name",
        "phone_number",
    )


class EZWICHDepositViewSet(BaseTicketViewSet):
    queryset = EZWICHDeposit.objects.all()
    serializer_class = EZWICHDepositSerializer
    filterset_class = EZWICHDepositFilter
    search_fields = (
        "ticket__ticket_number",
        "ezwich_card_number",
        "name",
        "phone_number",
    )


class MobileMoneyDepositViewSet(BaseTicketViewSet):
    queryset = MobileMoneyDeposit.objects.all()
    serializer_class = MobileMoneyDepositSerializer
    filterset_class = MobileMoneyDepositFilter
    search_fields = ("ticket__ticket_number", "name", "phone_number")
