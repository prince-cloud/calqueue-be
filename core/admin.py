from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
    Ticket,
    Verification,
)

BASE_READONLY = ("uuid", "created_at", "updated_at")
BASE_FILTER = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = (
        "ticket_number",
        "branch",
        "status",
        "phone_number",
        "servced_by",
        "processed_services_count",
        "created_at",
    )
    list_filter = BASE_FILTER + ("status", "branch")
    search_fields = ("ticket_number", "phone_number", "id_number")
    readonly_fields = (
        "uuid",
        "ticket_number",
        "services_data",
        "processed_services_count",
        "waiting_time",
        "called_time",
        "start_serve_time",
        "served_time",
        "total_time_spent",
        "created_at",
        "updated_at",
    )


@admin.register(Verification)
class VerificationAdmin(ModelAdmin):
    list_display = ("card_number", "verified", "created_at")
    list_filter = ("verified", "created_at")
    search_fields = ("card_number",)
    # readonly_fields = ("uuid", "card_number", "image", "verified", "data", "created_at")


@admin.register(CashDeposit)
class CashDepositTicketAdmin(ModelAdmin):
    list_display = ("deposit_type", "account_number", "depositor_name", "amount", "served_by", "created_at")
    list_filter = BASE_FILTER + ("deposit_type",)
    search_fields = ("account_number", "depositor_name", "phone_number")
    readonly_fields = BASE_READONLY


@admin.register(ChequeDeposit)
class ChequeDepositTicketAdmin(ModelAdmin):
    list_display = ("cheque_type", "beneficiary_account_number", "depositor_name", "served_by", "created_at")
    list_filter = BASE_FILTER + ("cheque_type",)
    search_fields = ("beneficiary_account_number", "depositor_name", "phone_number")
    readonly_fields = BASE_READONLY


@admin.register(EZWICHDeposit)
class EZWICHDepositTicketAdmin(ModelAdmin):
    list_display = ("ezwich_card_number", "name", "amount", "served_by", "created_at")
    list_filter = BASE_FILTER
    search_fields = ("ezwich_card_number", "name", "phone_number")
    readonly_fields = BASE_READONLY


@admin.register(MobileMoneyDeposit)
class MobileMoneyDepositTicketAdmin(ModelAdmin):
    list_display = ("name", "phone_number", "amount", "served_by", "created_at")
    list_filter = BASE_FILTER
    search_fields = ("name", "phone_number")
    readonly_fields = BASE_READONLY
