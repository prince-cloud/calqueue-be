from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    Branch,
    BranchTVConfig,
    BranchVoiceConfig,
    BranchWorkingHours,
    Counter,
    Device,
    MainService,
    Service,
    SystemVoiceConfig,
    TVAdvertisement,
)


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


@admin.register(Counter)
class CounterAdmin(ModelAdmin):
    list_display = ("counter_name", "counter_code", "branch", "counter_type", "is_active", "is_backoffice")
    list_filter = ("is_active", "is_backoffice", "counter_type", "branch")
    search_fields = ("counter_name", "counter_code")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(SystemVoiceConfig)
class SystemVoiceConfigAdmin(ModelAdmin):
    list_display = ("engine", "voice", "rate", "language", "slow", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not SystemVoiceConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BranchVoiceConfig)
class BranchVoiceConfigAdmin(ModelAdmin):
    list_display = ("branch", "engine", "voice", "rate", "language", "slow", "updated_at")
    list_filter = ("engine", "branch")
    search_fields = ("branch__name", "voice")
    readonly_fields = ("updated_at",)


class TVAdvertisementInline(TabularInline):
    model = TVAdvertisement
    extra = 0
    fields = ("media_type", "file", "order")
    ordering = ("order", "created_at")


@admin.register(BranchTVConfig)
class BranchTVConfigAdmin(ModelAdmin):
    list_display = ("branch", "show_ads", "updated_at")
    list_filter = ("show_ads",)
    search_fields = ("branch__name",)
    readonly_fields = ("updated_at",)
    inlines = (TVAdvertisementInline,)


@admin.register(TVAdvertisement)
class TVAdvertisementAdmin(ModelAdmin):
    list_display = ("tv_config", "media_type", "order", "created_at")
    list_filter = ("media_type",)
    readonly_fields = ("created_at",)
