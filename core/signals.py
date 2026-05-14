from django.db import models
from django.db.models.signals import post_save

from .models import CashDeposit, ChequeDeposit, EZWICHDeposit, MobileMoneyDeposit, Ticket

# Maps each service model → the service_type string stored in services_data
_MODEL_TO_SERVICE_TYPE = {
    CashDeposit: "CASH DEPOSIT",
    ChequeDeposit: "CHEQUE DEPOSIT",
    EZWICHDeposit: "EZWICH CARD DEPOSIT",
    MobileMoneyDeposit: "MOBILE MONEY DEPOSIT",
}


def _inject_object_uuid(sender, instance, created, **kwargs):
    """
    After a service model record is created with a ticket FK, find its matching
    entry in ticket.services_data, write the object UUID in, and increment
    processed_services_count for efficient "fully processed" queries.
    """
    if not created or not instance.ticket_id:
        return

    service_type = _MODEL_TO_SERVICE_TYPE[sender]

    # Fresh fetch so we always work from the latest services_data
    ticket = Ticket.objects.get(pk=instance.ticket_id)
    for item in ticket.services_data:
        if item.get("service_type") == service_type:
            item["object_uuid"] = str(instance.uuid)
            break

    ticket.processed_services_count = models.F("processed_services_count") + 1
    ticket.save(update_fields=["services_data", "processed_services_count", "updated_at"])


for _model in _MODEL_TO_SERVICE_TYPE:
    post_save.connect(_inject_object_uuid, sender=_model)
