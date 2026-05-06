from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Branch, BranchWorkingHours, Device


class BranchWorkingHoursInline(TabularInline):
    model = BranchWorkingHours
    extra = 0
    fields = ("day", "is_closed", "open_time", "close_time")
    ordering = ("day",)


@admin.register(Branch)
class BranchAdmin(ModelAdmin):
    list_display = ("name", "code", "location", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    inlines = (BranchWorkingHoursInline,)


@admin.register(Device)
class DeviceAdmin(ModelAdmin):
    list_display = (
        "label",
        "username",
        "device_id",
        "serial_number",
        "branch",
        "is_active",
        "last_login",
    )
    list_filter = ("is_active", "branch")
    search_fields = ("username", "device_id", "serial_number", "label")
    readonly_fields = ("device_id", "last_login", "created_at", "updated_at")
