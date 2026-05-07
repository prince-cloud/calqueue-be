from uuid import uuid4
from django.db import models, transaction
from django.utils import timezone
from configuration.models import Branch, Device, Service


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
