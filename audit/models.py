from django.conf import settings
from django.db import models


class APILog(models.Model):
    method = models.CharField(max_length=10)
    path = models.TextField()
    query_params = models.JSONField(default=dict, blank=True)
    request_body = models.JSONField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    status_code = models.PositiveSmallIntegerField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="api_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API Log"
        verbose_name_plural = "API Logs"

    def __str__(self):
        user_str = str(self.user) if self.user_id else "anonymous"
        return f"[{self.method}] {self.path} → {self.status_code} ({user_str})"


class LogEntry(models.Model):
    class Action(models.IntegerChoices):
        CREATE = 0, "Create"
        UPDATE = 1, "Update"
        DELETE = 2, "Delete"

    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.CASCADE,
        related_name="audit_log",
    )
    object_pk = models.CharField(max_length=255)
    object_repr = models.TextField()
    action = models.PositiveSmallIntegerField(choices=Action.choices)
    changes = models.JSONField(default=dict)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_log_entries",
    )
    remote_addr = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Log Entry"
        verbose_name_plural = "Log Entries"

    def __str__(self):
        return f"{self.get_action_display()} — {self.object_repr} ({self.timestamp:%Y-%m-%d %H:%M})"
