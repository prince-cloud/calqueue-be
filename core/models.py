import random
import string
from uuid import uuid4

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from configuration.models import Branch, Counter, Device


def _generate_reference() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f"REF{timezone.now().strftime('%Y%m%d')}{suffix}"


def _generate_t24_reference() -> str:
    digits = ''.join(random.choices(string.digits, k=8))
    return f"FT{digits}"


class T24Status(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMMITTED = "COMMITTED", "Committed"
    FAILED_COMMIT = "FAILED_COMMIT", "Failed Commit"


class T24ReferenceMixin(models.Model):
    t24_reference = models.CharField(max_length=10, unique=True, null=True, blank=True, db_index=True)
    t24_status = models.CharField(
        max_length=20,
        choices=T24Status.choices,
        default=T24Status.PENDING,
    )
    t24_response = models.JSONField(null=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.t24_reference:
            for _ in range(10):
                ref = _generate_t24_reference()
                if not self.__class__.objects.filter(t24_reference=ref).exists():
                    self.t24_reference = ref
                    self.t24_status = T24Status.COMMITTED
                    break
        super().save(*args, **kwargs)


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
    reference_number = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)

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

    services_data = models.JSONField(
        default=list,
        help_text="Raw services payload submitted at ticket creation time.",
    )
    processed_services_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of services that have had their model object created.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = []
        indexes = [
            # Most reports filter by branch + date range
            models.Index(fields=["branch", "created_at"], name="ticket_branch_date_idx"),
            # Performance / status reports filter by status + date
            models.Index(fields=["status", "created_at"], name="ticket_status_date_idx"),
            # Teller performance queries
            models.Index(fields=["servced_by", "status"], name="ticket_teller_status_idx"),
            # GIN index enables fast JSON containment queries on services_data
            GinIndex(fields=["services_data"], name="ticket_services_data_gin_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.reference_number:
            for _ in range(10):
                ref = _generate_reference()
                if not Ticket.objects.filter(reference_number=ref).exists():
                    self.reference_number = ref
                    break
        super().save(*args, **kwargs)

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



# ---------------------------------------------------------------------------
# Deposit tickets
# ---------------------------------------------------------------------------


class CashDeposit(T24ReferenceMixin, models.Model):
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
    served_by = models.ForeignKey(
        "accounts.CustomUser",
        related_name="cash_deposits_served",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — Cash Deposit ({self.deposit_type})"


class ChequeDeposit(T24ReferenceMixin, models.Model):
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
    served_by = models.ForeignKey(
        "accounts.CustomUser",
        related_name="cheque_deposits_served",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — Cheque Deposit ({self.cheque_type})"


class EZWICHDeposit(T24ReferenceMixin, models.Model):
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
    served_by = models.ForeignKey(
        "accounts.CustomUser",
        related_name="ezwich_deposits_served",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — EZWICHCard Deposit"


class MobileMoneyDeposit(T24ReferenceMixin, models.Model):
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
    served_by = models.ForeignKey(
        "accounts.CustomUser",
        related_name="mobile_money_deposits_served",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        num = self.ticket.ticket_number if self.ticket_id else "—"
        return f"{num} — Mobile Money Deposit"
