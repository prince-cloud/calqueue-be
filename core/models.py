from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models

from configuration.models import Branch, Counter, Device, Service


# ---------------------------------------------------------------------------
# Ticket (one queue position; multiple catalogue services via TicketService)
# ---------------------------------------------------------------------------


class TicketStatus(models.TextChoices):
    WAITING = "WAITING", "Waiting"
    ON_GOING = "ON_GOING", "On going"
    ON_HOLD = "ON_HOLD", "On hold"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    SKIPPED = "SKIPPED", "Skipped"


class Ticket(models.Model):
    """
    Single queue token for a visit. Tellers serve the ticket as a unit; related
    rows on TicketService describe which catalogue services are bundled.
    """

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    ticket_number = models.CharField(max_length=20, db_index=True)

    branch = models.ForeignKey(
        Branch,
        related_name="tickets",
        on_delete=models.PROTECT,
    )
    device = models.ForeignKey(
        Device,
        related_name="tickets_created",
        on_delete=models.PROTECT,
        help_text="Kiosk / device that issued the ticket.",
    )

    phone_number = models.CharField(max_length=20)
    id_number = models.CharField(max_length=50)
    id_type = models.CharField(max_length=50)
    signature = models.FileField(upload_to="ticket_signatures/", null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.WAITING,
        db_index=True,
    )

    counter = models.ForeignKey(
        Counter,
        related_name="tickets_served",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    servced_by = models.ForeignKey(
        "accounts.CustomUser",
        related_name="tickets_served",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ticket_audio = models.FileField(upload_to="ticket_audio/", null=True, blank=True)
    # Time DATA
    waiting_time = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Seconds from issue until called.",
    )
    called_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the ticket was first called.",
    )
    start_serve_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When serving started at the counter.",
    )
    served_time = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Seconds from start of serve until completed (optional).",
    )
    total_time_spent = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Seconds from issue until visit completed (optional).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("branch", "ticket_number"),
                name="core_ticket_branch_ticket_number_uniq",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.device_id
            and self.branch_id
            and self.device.branch_id != self.branch_id
        ):
            raise ValidationError(
                {"branch": "Branch must match the issuing device's branch."}
            )

    def __str__(self):
        return (
            f"{self.branch.code} — {self.ticket_number} ({self.get_status_display()})"
        )


class TicketService(models.Model):
    """
    One catalogue service attached to a ticket (display / teller checklist).
    Queue position and lifecycle belong to Ticket, not to each row here.
    """

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="ticket_services",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="ticket_services",
    )
    position = models.PositiveSmallIntegerField(
        default=0,
        help_text="Order of services as requested (0 = first).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ticket", "position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("ticket", "position"),
                name="core_ticketservice_ticket_position_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.ticket.ticket_number}: {self.service} @ {self.position}"


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

    ticket = models.ForeignKey(
        Ticket,
        related_name="cash_deposits",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — Cash Deposit ({self.deposit_type})"


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

    ticket = models.ForeignKey(
        Ticket,
        related_name="cheque_deposits",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — Cheque Deposit ({self.cheque_type})"


class EZWICHDeposit(models.Model):
    id_type = models.CharField(max_length=50)
    id_number = models.CharField(max_length=50)
    ezwich_card_number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    name = models.CharField(max_length=100)
    residential_address = models.TextField()
    occupation = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)

    ticket = models.ForeignKey(
        Ticket,
        related_name="ezwich_deposits",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — EZWICHCard Deposit"


class MobileMoneyDeposit(models.Model):
    id_type = models.CharField(max_length=50)
    id_number = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    residential_address = models.TextField()
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    occupation = models.CharField(max_length=100)

    ticket = models.ForeignKey(
        Ticket,
        related_name="mobile_money_deposits",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — Mobile Money Deposit"
