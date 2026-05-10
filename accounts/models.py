from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
from uuid import uuid4
from django.utils import timezone
from django.core.cache import cache
from audit.registry import auditlog


class CustomUser(AbstractUser):
    # AUTHENTICATION
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    phone_number = PhoneNumberField(blank=True, null=True, unique=True)

    # PROFILE
    fullname = models.CharField(max_length=240, null=True, blank=True)
    profile_picture = models.ImageField(max_length=100, null=True, blank=True)

    # MOBILE APP INFO
    fcm_app_token = models.CharField(max_length=240, null=True, blank=True)

    # OTHER INFO
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    deactivated_account = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{}:{}".format(self.fullname, self.email)

    def save(self, *args, **kwargs):
        self.fullname = self.get_full_name()

        if not self.username:
            self.username = self.phone_number

        # clear cached for object
        cache.delete(f"user_profile_{self.uuid}")
        return super().save(*args, **kwargs)

    def can_update(self):
        return self.last_updated <= timezone.now() - timezone.timedelta(days=90)


auditlog.register(CustomUser, exclude_fields=["password", "last_login"])


class UserID(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)

    class IDType(models.TextChoices):
        GHANA_CARD = "Ghana Card"
        DRIVING_LICENSE = "Driving License"
        PASSPORT = "Passport"
        VOTER_ID = "Voter ID"
        OTHER = "Other"

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="user_identity",
    )
    id_type = models.CharField(
        max_length=20,
        choices=IDType.choices,
    )
    id_number = models.CharField(max_length=20)
    id_front_image = models.ImageField(
        upload_to="id_front_images/", null=True, blank=True
    )
    id_back_image = models.ImageField(
        upload_to="id_back_images/", null=True, blank=True
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.id_number

    def can_update(self):
        return self.last_updated <= timezone.now() - timezone.timedelta(days=90)


class UserAddress(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="user_address",
    )
    gps_address = models.CharField(max_length=20)
    address = models.TextField(null=True, blank=True)
    nearest_landmark = models.CharField(max_length=20, null=True, blank=True)
    city = models.CharField(max_length=20, null=True, blank=True)
    region = models.CharField(max_length=20, null=True, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.fullname

    def can_update(self):
        return self.last_updated <= timezone.now() - timezone.timedelta(days=90)


auditlog.register(UserID)
auditlog.register(UserAddress)
