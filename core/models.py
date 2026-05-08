from uuid import uuid4
from django.db import models, transaction
from django.utils import timezone
from configuration.models import Branch, Device, Service


# ---------------------------------------------------------------------------
# Ticket Modeling
# ---------------------------------------------------------------------------
# class TicketStatus(models.Model):
#     WAITING = "Waiting"
#     ON_GOING = "On Going"
#     ON_HOLD = "On Hold"
#     COMPLETED = "Completed"
#     CANCLLED = "Cancelled"
#     SKIPPED = "Skipped"


# class Ticket(models.Model):

#     branch = models.ForeignKey(
#         Branch,
#         related_name="tickets",
#         null=True,
#         on_delete=models.SET_NULL,
#     )
#     assigned_to = models.ForeignKey(
#         CustomUser,
#         related_name="tickets_assigned",
#         null=True,
#         on_delete=models.SET_NULL,
#     )
#     customer = models.ForeignKey(
#         Customer,
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name="tickets",
#     )

#     ticket_number = models.CharField(max_length=20)

#     ticket_audio = models.FileField(upload_to="ticket_audio/", null=True, blank=True)
#     signature = models.ImageField(upload_to="ticket_signatures/", null=True, blank=True)

#     waiting_time = models.PositiveIntegerField(
#         null=True,
#         blank=True,
#         help_text="Waiting time (in seconds)",
#         default=0,
#     )
#     called_time = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Time ticket was called",
#     )
#     start_serve_time = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="Time ticket was started to be served",
#     )
#     served_time = models.PositiveIntegerField(
#         null=True,
#         blank=True,
#         help_text="Serving time (in seconds)",
#         default=0,
#     )
#     total_time_spent = models.PositiveIntegerField(
#         null=True,
#         blank=True,
#         help_text="Total Time spent at branch (in seconds)",
#         default=0,
#     )

#     counter = models.ForeignKey(
#         Counter,
#         related_name="tickets_served",
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#     )

#     status = models.CharField(
#         choices=Status.choices,
#         max_length=50,
#         default=Status.WAITING,
#     )

#     hold_reason = models.CharField(
#         max_length=300,
#         null=True,
#         blank=True,
#     )

#     from_device = models.ForeignKey(
#         Device,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#     )

#     uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return "{} - {}".format(
#             date=self.created_at,
#             ticket_number=self.ticket_number,
#         )


# ---------------------------------------------------------------------------
# Deposit tickets
# ---------------------------------------------------------------------------


class CashDeposit(models.Model):
    class DepositType(models.TextChoices):
        SELF = "SELF", "Self"
        THIRD_PARTY = "THIRD PARTY", "Third Party"

    deposit_type = models.CharField(
        max_length=20, choices=DepositType.choices, db_index=True
    )
    account_number = models.CharField(max_length=30, db_index=True)
    account_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    phone_number = models.CharField(max_length=20)
    depositor_name = models.CharField(max_length=100)

    # Third Party only
    residential_address = models.TextField(null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    id_type = models.CharField(max_length=50, null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticket_number} — Cash Deposit ({self.deposit_type})"


class ChequeDeposit(models.Model):
    class ChequeType(models.TextChoices):
        CALBANK = "CALBANK", "CalBank Cheque"
        OTHER_BANK = "OTHER BANK", "Other Bank Cheque"

    cheque_type = models.CharField(
        max_length=20, choices=ChequeType.choices, db_index=True
    )
    beneficiary_account_number = models.CharField(max_length=30, db_index=True)
    beneficiary_account_name = models.CharField(max_length=100)
    cheque_details = models.TextField()
    phone_number = models.CharField(max_length=20)
    depositor_name = models.CharField(max_length=100)

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticket_number} — Cheque Deposit ({self.cheque_type})"


class EZWICHDeposit(models.Model):
    id_type = models.CharField(max_length=50)
    id_number = models.CharField(max_length=50)
    ezwich_card_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    name = models.CharField(max_length=100)
    residential_address = models.TextField()
    occupation = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticket_number} — EZWICHCard Deposit"


class MobileMoneyDeposit(models.Model):
    id_type = models.CharField(max_length=50)
    id_number = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    residential_address = models.TextField()
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    occupation = models.CharField(max_length=100)

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticket_number} — Mobile Money Deposit"
