from django.db import models
from django.core.exceptions import ValidationError
from auditlog.registry import auditlog
import uuid


class Branch(models.Model):
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
    class Day(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="working_hours",
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
                raise ValidationError("Open and close times are required when the branch is not closed.")
            if self.open_time >= self.close_time:
                raise ValidationError("Open time must be before close time.")


class Device(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    device_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    serial_number = models.CharField(max_length=100, unique=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="devices",
    )
    label = models.CharField(max_length=100, blank=True, help_text="e.g. Teller Counter 1")
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


auditlog.register(Branch)
auditlog.register(BranchWorkingHours)
auditlog.register(Device, exclude_fields=["password"])
