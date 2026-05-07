from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Branch, BranchWorkingHours, Device, MainService, Service


class BranchWorkingHoursInline(TabularInline):
    model = BranchWorkingHours
    extra = 0
    fields = ("day", "is_closed", "open_time", "close_time")
    ordering = ("day",)


class ServiceInline(TabularInline):
    model = Service
    extra = 0
    fields = ("name", "icon", "description", "is_active")
    show_change_link = True


@admin.register(Branch)
class BranchAdmin(ModelAdmin):
    list_display = ("name", "code", "location", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = (BranchWorkingHoursInline,)


@admin.register(Device)
class DeviceAdmin(ModelAdmin):
    list_display = ("label", "username", "device_id", "serial_number", "branch", "is_active", "last_login")
    list_filter = ("is_active", "branch")
    search_fields = ("username", "device_id", "serial_number", "label")
    readonly_fields = ("uuid", "device_id", "last_login", "created_at", "updated_at")


@admin.register(MainService)
class MainServiceAdmin(ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = (ServiceInline,)


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ("name", "main_service", "is_active", "created_at")
    list_filter = ("is_active", "main_service")
    search_fields = ("name",)
    readonly_fields = ("uuid", "created_at", "updated_at")
