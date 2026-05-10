from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import APILog, LogEntry


@admin.register(APILog)
class APILogAdmin(ModelAdmin):
    list_display = ("id","method", "path", "status_code", "user", "ip_address", "duration_ms", "created_at")
    list_filter = ("method", "status_code", "created_at")
    search_fields = ("path", "user__email", "ip_address", "error_message")
    readonly_fields = (
        "method", "path", "query_params", "request_body", "response_body",
        "status_code", "user", "ip_address", "user_agent", "error_message",
        "duration_ms", "created_at",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogEntry)
class LogEntryAdmin(ModelAdmin):
    list_display = ("id","action", "object_repr", "content_type", "actor", "remote_addr", "timestamp")
    list_filter = ("action", "content_type", "timestamp")
    search_fields = ("object_repr", "object_pk", "actor__email")
    readonly_fields = (
        "content_type", "object_pk", "object_repr", "action",
        "changes", "actor", "remote_addr", "timestamp",
    )
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
