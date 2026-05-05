from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from . import models


@admin.register(models.CustomUser)
class UserAdmin(UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    readonly_fields = ("fcm_app_token", "uuid")
    list_display = [
        "id",
        "fullname",
        "phone_number",
        "email",
        "deactivated_account",
    ]
    fieldsets = [*UserAdmin.fieldsets]
    fieldsets.insert(
        2,
        (
            None,
            {
                "fields": (
                    "fullname",
                    "phone_number",
                    "profile_picture",
                    "fcm_app_token",
                    "deactivated_account",
                    "uuid",
                ),
            },
        ),
    )


@admin.register(models.UserID)
class UserIDAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "id_type",
        "id_number",
    ]


@admin.register(models.UserAddress)
class UserAddressAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "gps_address",
        "address",
        "nearest_landmark",
        "city",
        "region",
    ]
