import django_filters

from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
)


class BaseFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name="created_at", lookup_expr="date")
    date_from = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__gte"
    )
    date_to = django_filters.DateFilter(
        field_name="created_at", lookup_expr="date__lte"
    )


class CashDepositFilter(BaseFilter):
    amount_min = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = CashDeposit
        fields = (
            "deposit_type",
            "date",
            "date_from",
            "date_to",
        )


class ChequeDepositFilter(BaseFilter):
    class Meta:
        model = ChequeDeposit
        fields = (
            "cheque_type",
            "date",
            "date_from",
            "date_to",
        )


class EZWICHDepositFilter(BaseFilter):
    amount_min = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = EZWICHDeposit
        fields = ("date", "date_from", "date_to")


class MobileMoneyDepositFilter(BaseFilter):
    amount_min = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = MobileMoneyDeposit
        fields = ("date", "date_from", "date_to")
