from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
)

BASE_READONLY = ("uuid", "created_at", "updated_at")
BASE_FILTER = ("created_at",)


@admin.register(CashDeposit)
class CashDepositTicketAdmin(ModelAdmin):
    list_display = (
        "deposit_type",
        "account_number",
        "depositor_name",
        "amount",
        "created_at",
    )
    list_filter = BASE_FILTER + ("deposit_type",)
    search_fields = (
        "account_number",
        "depositor_name",
        "phone_number",
    )
    readonly_fields = BASE_READONLY


@admin.register(ChequeDeposit)
class ChequeDepositTicketAdmin(ModelAdmin):
    list_display = (
        "cheque_type",
        "beneficiary_account_number",
        "depositor_name",
        "created_at",
    )
    list_filter = BASE_FILTER + ("cheque_type",)
    search_fields = (
        "beneficiary_account_number",
        "depositor_name",
        "phone_number",
    )
    readonly_fields = BASE_READONLY


@admin.register(EZWICHDeposit)
class EZWICHDepositTicketAdmin(ModelAdmin):
    list_display = (
        "ezwich_card_number",
        "name",
        "amount",
        "created_at",
    )
    list_filter = BASE_FILTER
    search_fields = ("ezwich_card_number", "name", "phone_number")
    readonly_fields = BASE_READONLY


@admin.register(MobileMoneyDeposit)
class MobileMoneyDepositTicketAdmin(ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "amount",
        "created_at",
    )
    list_filter = BASE_FILTER
    search_fields = ("name", "phone_number")
    readonly_fields = BASE_READONLY
