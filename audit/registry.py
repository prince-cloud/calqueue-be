import decimal
import uuid
from datetime import date, datetime, time

from django.db.models.signals import post_save, pre_delete, pre_save


def _serialize(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value)


def _snapshot(instance, exclude_fields):
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in exclude_fields or field.attname in exclude_fields:
            continue
        try:
            data[field.name] = _serialize(field.value_from_object(instance))
        except Exception:
            pass
    return data


class AuditRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, model, exclude_fields=None):
        if model in self._registry:
            return
        self._registry[model] = set(exclude_fields or [])
        pre_save.connect(self._pre_save, sender=model, weak=False)
        post_save.connect(self._post_save, sender=model, weak=False)
        pre_delete.connect(self._pre_delete, sender=model, weak=False)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _pre_save(self, sender, instance, **kwargs):
        if not instance.pk:
            instance._audit_old_state = None
            return
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._audit_old_state = _snapshot(old, self._registry[sender])
        except sender.DoesNotExist:
            instance._audit_old_state = None

    def _post_save(self, sender, instance, created, **kwargs):
        from django.contrib.contenttypes.models import ContentType

        from .context import get_actor
        from .models import LogEntry

        exclude = self._registry[sender]
        new_state = _snapshot(instance, exclude)

        if created:
            action = LogEntry.Action.CREATE
            changes = {k: [None, v] for k, v in new_state.items()}
        else:
            old_state = getattr(instance, "_audit_old_state", None) or {}
            changes = {k: [old_state.get(k), v] for k, v in new_state.items() if old_state.get(k) != v}
            if not changes:
                return
            action = LogEntry.Action.UPDATE

        LogEntry.objects.create(
            content_type=ContentType.objects.get_for_model(sender),
            object_pk=str(instance.pk),
            object_repr=str(instance)[:200],
            action=action,
            changes=changes,
            actor=get_actor(),
        )

    def _pre_delete(self, sender, instance, **kwargs):
        from django.contrib.contenttypes.models import ContentType

        from .context import get_actor
        from .models import LogEntry

        exclude = self._registry[sender]
        old_state = _snapshot(instance, exclude)

        LogEntry.objects.create(
            content_type=ContentType.objects.get_for_model(sender),
            object_pk=str(instance.pk),
            object_repr=str(instance)[:200],
            action=LogEntry.Action.DELETE,
            changes={k: [v, None] for k, v in old_state.items()},
            actor=get_actor(),
        )


auditlog = AuditRegistry()
