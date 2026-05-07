import uuid as _uuid
from uuid import uuid4
from django.db import models
from django.core.exceptions import ValidationError
from auditlog.registry import auditlog


# ---------------------------------------------------------------------------
# Branch
# ---------------------------------------------------------------------------


class Branch(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    location = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "branches"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class BranchWorkingHours(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)

    class Day(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="working_hours"
    )
    day = models.IntegerField(choices=Day.choices)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("branch", "day")
        ordering = ["day"]
        verbose_name_plural = "branch working hours"

    def __str__(self):
        if self.is_closed:
            return f"{self.branch.code} — {self.get_day_display()}: Closed"
        return f"{self.branch.code} — {self.get_day_display()}: {self.open_time} – {self.close_time}"

    def clean(self):
        if not self.is_closed:
            if not self.open_time or not self.close_time:
                raise ValidationError(
                    "Open and close times are required when the branch is not closed."
                )
            if self.open_time >= self.close_time:
                raise ValidationError("Open time must be before close time.")


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------


class Device(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    device_id = models.CharField(max_length=100, unique=True, default=uuid4)
    serial_number = models.CharField(max_length=100, unique=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="devices")
    label = models.CharField(
        max_length=100, blank=True, help_text="e.g. Teller Counter 1"
    )
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["branch", "label"]

    def __str__(self):
        return f"{self.label or self.username} — {self.branch.code}"

    def check_password(self, raw_password: str) -> bool:
        return self.password == raw_password

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Service catalogue
# ---------------------------------------------------------------------------


class MainServiceTypes(models.TextChoices):
    DEPOSIT = "DEPOSIT", "Deposit"
    WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
    TRANSFER = "TRANSFER", "Transfer"
    REQUESTS = "REQUESTS", "Requests"
    SET_PIN = "SET PIN", "Set PIN"
    OTHER_TRANSACTIONS = "OTHER TRANSACTIONS", "Other Transactions"


class ServiceTypes(models.TextChoices):
    # Deposit
    CASH_DEPOSIT = "CASH DEPOSIT", "Cash Deposit"
    CHEQUE_DEPOSIT = "CHEQUE DEPOSIT", "Cheque Deposit"
    EZWICH_CARD_DEPOSIT = "EZWICH CARD DEPOSIT", "EZWICHCard Deposit"
    MOBILE_MONEY_DEPOSIT = "MOBILE MONEY DEPOSIT", "Mobile Money Deposit"
    # Withdrawal
    CASH_WITHDRAWAL = "CASH WITHDRAWAL", "Cash Withdrawal (Own Account)"
    CHEQUE_WITHDRAWAL = "CHEQUE WITHDRAWAL", "Cheque Withdrawal (Third Party)"
    FOREIGN_TO_LOCAL = "FOREIGN TO LOCAL", "Foreign to Local Currency (Third Party)"
    EZWICH_CARD_WITHDRAWAL = "EZWICH CARD WITHDRAWAL", "EZWICHCard Withdrawal"
    MOBILE_MONEY_WITHDRAWAL = "MOBILE MONEY WITHDRAWAL", "Mobile Money Withdrawal"
    FOREX_PURCHASE = "FOREX PURCHASE", "Forex Purchase"
    # Transfer
    FUNDS_TRANSFER = "FUNDS TRANSFER", "Funds Transfer"
    GHIPPS_INSTANT_PAY = "GHIPPS INSTANT PAY", "GHIPPS Instant Pay (GIP)"
    # Requests
    STATEMENT_REQUEST = "STATEMENT REQUEST", "Statement Request"
    CHEQUE_BOOK_REQUEST = "CHEQUE BOOK REQUEST", "Cheque Book Request"
    BALANCE_ENQUIRY = "BALANCE ENQUIRY", "Balance Enquiry Request"
    BANKERS_DRAFT_REQUEST = "BANKERS DRAFT REQUEST", "Bankers Draft Request"
    STOP_CHEQUE = "STOP CHEQUE", "Stop Cheque"
    STANDING_ORDER = "STANDING ORDER", "Standing Order"
    # Set PIN
    SIGNUP = "SIGNUP", "SignUp"
    FORGOT_PIN = "FORGOT PIN", "Forgot PIN"
    ACTIVATE_PIN = "ACTIVATE PIN", "Activate PIN"


MAIN_SERVICE_MAP: dict[str, list[str]] = {
    MainServiceTypes.DEPOSIT: [
        ServiceTypes.CASH_DEPOSIT,
        ServiceTypes.CHEQUE_DEPOSIT,
        ServiceTypes.EZWICH_CARD_DEPOSIT,
        ServiceTypes.MOBILE_MONEY_DEPOSIT,
    ],
    MainServiceTypes.WITHDRAWAL: [
        ServiceTypes.CASH_WITHDRAWAL,
        ServiceTypes.CHEQUE_WITHDRAWAL,
        ServiceTypes.FOREIGN_TO_LOCAL,
        ServiceTypes.EZWICH_CARD_WITHDRAWAL,
        ServiceTypes.MOBILE_MONEY_WITHDRAWAL,
        ServiceTypes.FOREX_PURCHASE,
    ],
    MainServiceTypes.TRANSFER: [
        ServiceTypes.FUNDS_TRANSFER,
        ServiceTypes.GHIPPS_INSTANT_PAY,
    ],
    MainServiceTypes.REQUESTS: [
        ServiceTypes.STATEMENT_REQUEST,
        ServiceTypes.CHEQUE_BOOK_REQUEST,
        ServiceTypes.BALANCE_ENQUIRY,
        ServiceTypes.BANKERS_DRAFT_REQUEST,
        ServiceTypes.STOP_CHEQUE,
        ServiceTypes.STANDING_ORDER,
    ],
    MainServiceTypes.SET_PIN: [
        ServiceTypes.SIGNUP,
        ServiceTypes.FORGOT_PIN,
        ServiceTypes.ACTIVATE_PIN,
    ],
    MainServiceTypes.OTHER_TRANSACTIONS: [],
}


class MainService(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    name = models.CharField(
        choices=MainServiceTypes.choices, unique=True, max_length=50
    )
    is_active = models.BooleanField(default=True)
    icon = models.FileField(upload_to="main-services/", null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()


class Service(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    main_service = models.ForeignKey(
        MainService, related_name="services", on_delete=models.SET_NULL, null=True
    )
    name = models.CharField(choices=ServiceTypes.choices, unique=True, max_length=50)
    icon = models.FileField(upload_to="services/", null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.main_service_id and self.name:
            allowed = MAIN_SERVICE_MAP.get(self.main_service.name, [])
            if self.name not in allowed:
                raise ValidationError(
                    f"'{self.get_name_display()}' is not valid under '{self.main_service.get_name_display()}'."
                )

    def __str__(self):
        return self.get_name_display()


auditlog.register(Branch)
auditlog.register(BranchWorkingHours)
auditlog.register(Device, exclude_fields=["password"])
auditlog.register(MainService)
auditlog.register(Service)
