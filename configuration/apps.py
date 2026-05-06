from django.apps import AppConfig


class ConfigurationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "configuration"

    def ready(self):
        import configuration.models  # noqa: F401 — triggers auditlog.register() calls
