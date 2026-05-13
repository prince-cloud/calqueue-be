from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from . import models
from .models import UserApproval


@admin.register(models.CustomUser)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    readonly_fields = ("fcm_app_token", "uuid")
    list_display = ["uuid", "fullname", "email", "user_type", "branch", "is_active"]
    list_filter = ("user_type", "is_active", "branch")
    search_fields = ("email", "first_name", "last_name", "cbs_id")
    fieldsets = [*UserAdmin.fieldsets]
    fieldsets.insert(
        2,
        (
            "Profile",
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
    fieldsets.insert(
        3,
        (
            "Staff / System User",
            {
                "fields": (
                    "cbs_id",
                    "user_type",
                    "role",
                    "branch",
                    "queue_counter",
                    "t24_username",
                    "t24_login_required",
                ),
            },
        ),
    )


@admin.register(models.UserID)
class UserIDAdmin(ModelAdmin):
    list_display = ["uuid", "user", "id_type", "id_number"]
    readonly_fields = ("uuid", "date_created", "last_updated")


@admin.register(models.UserAddress)
class UserAddressAdmin(ModelAdmin):
    list_display = ["uuid", "user", "gps_address", "address", "city", "region"]
    readonly_fields = ("uuid", "date_created", "last_updated")


@admin.register(UserApproval)
class UserApprovalAdmin(ModelAdmin):
    list_display = ("user", "status", "processed_by", "processed_at", "created_at")
    list_filter = ("status",)
    readonly_fields = ("uuid", "created_at", "updated_at")
