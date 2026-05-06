from rest_framework import serializers
from .models import CustomUser, UserID, UserAddress
from dj_rest_auth.serializers import LoginSerializer
from datetime import datetime, timedelta
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from helpers import exceptions
from helpers.functions import generate_otp, email_address_exists
from django.db.models import Q
from django.http import HttpRequest
from django.db import transaction
from allauth.account.models import EmailAddress
from accounts.tasks import generic_send_mail, generic_send_sms
from phonenumber_field.serializerfields import PhoneNumberField
import secrets
from allauth.account.adapter import get_adapter
from django.core.exceptions import ValidationError as DjangoValidationError
from loguru import logger


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "fullname",
            "profile_picture",
            "can_update",
        )


class SignUpSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=50, required=True)
    last_name = serializers.CharField(max_length=15, min_length=3, required=True)
    phone_number = PhoneNumberField(allow_blank=False)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6)
    registration_token = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    cleaned_data = None

    def validate_registration_token(self, token: str) -> str:
        # if token != "":
        # if cache.get(f"registration/token/{token}"):
        #     return token
        # else:
        #     raise exceptions.InvalidOTPException()
        pass

    def validate_phone_number(self, phone_number):
        logger.debug("Validating phone number: {}", phone_number)
        try:
            user_number = CustomUser.objects.get(phone_number=phone_number)
            if user_number:
                raise exceptions.PhoneNumberAlreadyInUseException()
        except ObjectDoesNotExist:
            return phone_number
        return phone_number

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        if email and email_address_exists(email):
            raise exceptions.EmailAlreadyInUseException()
        return email

    def validate_password(self, password):
        return get_adapter().clean_password(password)

    def get_cleaned_data(self):
        return {
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
            "email": self.validated_data.get("email", ""),
            "password": self.validated_data.get("password", ""),
            "phone_number": self.validated_data.get("phone_number", ""),
        }

    @transaction.atomic
    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        user = adapter.save_user(request, user, self, commit=False)
        if "password" in self.cleaned_data:
            try:
                adapter.clean_password(self.cleaned_data["password"], user=user)
            except DjangoValidationError as exc:
                raise exceptions.InvalidPasswordException(detail=str(exc))
        user.phone_number = self.cleaned_data["phone_number"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()
        self.validated_data["email"] = user.email
        # create email address
        EmailAddress.objects.create(email=user.email, user=user)

        self.verify_account()
        return user

    def verify_account(self):
        email = self.validated_data["email"]
        phone_number = self.validated_data["phone_number"]
        if email:
            user_email = EmailAddress.objects.get(email=email)
            user_email.verified = True
            user_email.set_as_primary(conditional=True)
            user_email.save()
            user_account = CustomUser.objects.get(email=email)
            user_account.is_active = True
            user_account.save()
            user_account.backend = "allauth.account.auth_backends.AuthenticationBackend"
            self.validated_data["user"] = user_account
            return email
        user_account = CustomUser.objects.get(phone_number=phone_number)
        user_account.backend = "allauth.account.auth_backends.AuthenticationBackend"
        self.validated_data["user"] = user_account
        email = user_account.email
        user_email = EmailAddress.objects.get(email=email)
        user_email.verified = True
        user_email.set_as_primary(conditional=True)
        user_email.save()
        user_account.is_active = True
        user_account.save()
        return email


class CustomLoginSerializer(LoginSerializer):
    """
    Custom Login serializer to overide default dj-rest-auth login
    """

    def custom_validate(self, username):
        try:
            _username = CustomUser.objects.get(username=username)
            # print("=== username: ", _username)
            if not _username.is_active:
                # automatically generate and send otp to the user account.
                otp_generated = generate_otp(6)
                _username.otp = otp_generated
                _username.otp_expiry = datetime.now() + timedelta(minutes=5)
                _username.save()

                # send otp to the user's email
                # message = "OTP for your account verification is {}.".format(
                #     otp_generated
                # )
                # generic_send_mail.delay(
                #     message=message,
                #     recipient_list=_username.email,
                #     title="Account Verification OTP",
                # )
                # else if
                raise exceptions.InactiveAccountException()
        except ObjectDoesNotExist:
            return username

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def validate(self, attrs):
        request: HttpRequest = self.context.get("request")
        username = attrs.get("username")
        email = attrs.get("email")
        password = attrs.get("password")

        attempt = cache.get(f"login-attempt/{username}")
        if attempt:
            attempt += 1
        else:
            attempt = 1
        cache.set(f"login-attempt/{username}", attempt, 60 * 5)
        if attempt > 5:
            raise exceptions.TooManyLoginAttemptsException()

        if not (username or email):
            raise exceptions.ProvideUsernameOrPasswordException()

        if username:
            user_qs = CustomUser.objects.filter(
                Q(username=username) | Q(email=username) | Q(phone_number=username),
            )
            if user_qs.exists():
                user = user_qs.first()
                if user.deactivated_account:
                    raise exceptions.AccountDeactivatedException()
                email = user.email
                attrs["email"] = user.email

            else:
                raise exceptions.UsernameDoesNotExistsException()
        elif email:
            user_qs = CustomUser.objects.filter(email=email)
            if user_qs.exists():
                user = user_qs.first()
                if user.deactivated_account:
                    raise exceptions.AccountDeactivatedException()
                username = user.username
                attrs["username"] = user.username
            else:
                raise exceptions.EmailDoesNotExistsException()

        _ = self.custom_validate(username)
        user: CustomUser = self.get_auth_user(username, email, password)

        if not user:
            raise exceptions.LoginException()

        try:
            user.last_login_ip = self.get_client_ip(request)
            user.save()
        except Exception:
            pass
        cache.delete(f"login-attempt/{username}")
        attrs = super().validate(attrs)
        return attrs


class ResetPasswordOtpSerializer(serializers.Serializer):
    """
    this seriailzer sends an otp for password reset. this endpoints is
    used when the user has forggoten his/her password and wants to
    reset.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        if value:
            user_qs = CustomUser.objects.filter(email=value)
            if user_qs.exists():
                return user_qs.first()
            raise exceptions.EmailDoesNotExistsException()
        return None

    @transaction.atomic
    def save(self):
        email = self.validated_data.get("email")
        user: CustomUser = email

        # generate otp code
        otp_generated = generate_otp(6)
        logger.info("Password reset OTP generated for email: {}", user.email)
        # save otp in cache
        cache.set(f"password-reset-otp/{user.email}", otp_generated, 60 * 5)

        generic_send_mail.delay(
            recipient=str(user.email),
            title="Reset Password OTP",
            template_type="password_reset_otp",
            payload={
                "otp": otp_generated,
                "first_name": user.first_name or "User",
            },
        )
        return user


class ResetPasswordSerializer(serializers.Serializer):
    """
    this is the serializer for reseting password by providing otp sent
    for password reset and proviving your new password.
    """

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField()

    def validate_email(self, value):
        if value:
            user_qs = CustomUser.objects.filter(email=value)
            if user_qs.exists():
                return user_qs.first()
            raise exceptions.EmailDoesNotExistsException()
        return None

    def validate(self, attrs):
        email = attrs.get("email", "")
        otp = attrs.get("otp", "")

        if len(otp) != 6:
            raise exceptions.InvalidOTPException(detail="OTP length Invalid!")
        elif not email:
            raise exceptions.EmailOrUsernameRequiredException()

        user: CustomUser = email
        # check if token has expiered or not
        cached_otp = cache.get(f"password-reset-otp/{user.email}", None)
        if cached_otp != otp:
            raise exceptions.InvalidOTPException()
        return attrs

    @transaction.atomic
    def save(self):
        email = self.validated_data.get("email")
        password = self.validated_data.get("new_password")
        user: CustomUser = email

        # change password for user
        user.set_password(password)
        user.save()

        # send for a successful password change
        generic_send_mail.delay(
            recipient=str(user.email),
            title="Password Changed Successfully",
            template_type="password_changed",
            payload={
                "first_name": user.first_name or "User",
            },
        )
        return user


class VerifyResetPasswordOtpSerializer(serializers.Serializer):
    """
    this serializer checks and validate the otp sent for password reset
    """

    otp = serializers.CharField(max_length=6)
    username_email = serializers.CharField(max_length=100)

    def validate_username_email(self, value):
        if value:
            user_qs = CustomUser.objects.filter(Q(email=value) | Q(username=value))
            if user_qs.exists():
                return user_qs.first()
            raise exceptions.AccountDoesNotExistException()
        return None

    def validate(self, attrs):
        username_email = attrs.get("username_email", "")
        otp = attrs.get("otp", "")

        if len(otp) != 6:
            raise exceptions.InvalidOTPException(detail="OTP length Invalid!")
        elif not username_email:
            raise exceptions.EmailOrUsernameRequiredException()

        user: CustomUser = username_email
        # check if token has expiered or not
        cached_otp = cache.get(f"password-reset-otp/{user.email}", None)
        if cached_otp != otp:
            raise exceptions.InvalidOTPException()
        return attrs

    @transaction.atomic
    def save(self):
        email_username = self.validated_data.get("username_email")
        user: CustomUser = email_username
        return user


class UserIDSerializer(serializers.ModelSerializer):
    can_update = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserID
        fields = (
            "id",
            "id_type",
            "id_number",
            "id_front_image",
            "id_back_image",
            "date_created",
            "last_updated",
            "can_update",
        )
        read_only_fields = ("id", "date_created", "last_updated")

    def get_can_update(self, obj):
        return obj.can_update() if obj else True

    def validate(self, attrs):
        # If updating an existing instance, check if update is allowed
        if self.instance and not self.instance.can_update():
            from helpers import exceptions

            raise exceptions.UpdateNotAllowedException()
        return attrs


class UserAddressSerializer(serializers.ModelSerializer):
    can_update = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserAddress
        fields = (
            "id",
            "gps_address",
            "address",
            "nearest_landmark",
            "city",
            "region",
            "date_created",
            "last_updated",
            "can_update",
        )
        read_only_fields = ("id", "date_created", "last_updated")

    def get_can_update(self, obj):
        return obj.can_update() if obj else True

    def validate(self, attrs):
        # If updating an existing instance, check if update is allowed
        if self.instance and not self.instance.can_update():
            from helpers import exceptions

            raise exceptions.UpdateNotAllowedException()
        return attrs


class SendPhoneNumberOTPSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(allow_blank=False)

    def send_email(self, request):
        """Send email Generate OTP and key and saves them in user account,
        Sends email with an otp to user for Account Activation"""
        phone_number = self.validated_data["phone_number"]
        otp = generate_otp(6)

        # validate if customer with the phone number exists
        if CustomUser.objects.filter(
            phone_number=phone_number,
        ).exists():
            raise exceptions.PhoneNumberAlreadyInUseException()

        logger.info("Phone number OTP generated: {}", phone_number)

        cache.set(f"otp/phone_number/{phone_number}", otp, 60 * 5)

        body = f"""
Your one-time password (OTP) for account verification is: {otp}.
Please enter it to continue. If you didn't request this, feel free to ignore the message.
        """

        generic_send_sms.delay(to=str(phone_number), body=body)

        return self.validated_data["phone_number"]


class SendEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(allow_blank=False)

    def send_email(self, request):
        """Send email Generate OTP and key and saves them in user account,
        Sends email with an otp to user for Account Activation"""
        email = self.validated_data["email"]
        otp = generate_otp(6)

        # validate if customer with the phone number exists
        if CustomUser.objects.filter(
            email=email,
        ).exists():
            raise exceptions.EmailAlreadyInUseException()

        cache.set(f"otp/email/{email}", otp, 60 * 4)

        generic_send_mail.delay(
            recipient=str(email),
            title="Email Verification OTP",
            template_type="email_otp_verification",
            payload={
                "otp": otp,
            },
        )

        return self.validated_data["email"]


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = PhoneNumberField(allow_blank=False, required=False)
    email = serializers.EmailField(allow_blank=False, required=False)
    # email = serializers.EmailField(required=False)
    otp = serializers.CharField(max_length=6, min_length=6, required=True)
    registration_token = serializers.SerializerMethodField(read_only=True)
    token: str = ""

    def get_registration_token(self, *args, **kwargs):
        return self.token

    def verify_otp(self, request) -> str:
        """Send email Generate OTP and key and saves them in user account,
        Sends email with an otp to user for Account Activation"""
        # email = self.validated_data["email"]
        phone_number = self.validated_data.get("phone_number", None)
        email = self.validated_data.get("email", None)
        otp = self.validated_data["otp"]

        logger.debug("Verifying OTP - phone: {}, email: {}", phone_number, email)
        # get token details from cache for a maximum of 24 hours
        if phone_number:
            cache_otp_value = cache.get(f"otp/phone_number/{phone_number}")
        elif email:
            cache_otp_value = cache.get(f"otp/email/{email}")
        else:
            raise exceptions.InvalidOTPException()

        if cache_otp_value == otp:
            while True:
                token = secrets.token_urlsafe(16)
                if cache.add(
                    f"registration/token/{token}",
                    {"phone_number": str(phone_number), "email": email},
                    60 * 60 * 24,
                ):
                    self.token = token
                    break

        else:
            raise exceptions.InvalidOTPException()
        return self.token


class FCMAppTokenSerializer(serializers.ModelSerializer):
    """
    Firebase Clouse messaging app token serializer
    Storing user's app fcm app token
    """

    class Meta:
        model = CustomUser
        fields = ("fcm_app_token",)


class ProfilePictureSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile picture and phone number
    """

    phone_number = PhoneNumberField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = ("profile_picture", "phone_number")

    def validate_phone_number(self, phone_number):
        """Validate that phone number is unique if provided."""
        if phone_number:
            # Check if phone number is already used by another user
            existing_user = (
                CustomUser.objects.filter(phone_number=phone_number)
                .exclude(id=self.instance.id if self.instance else None)
                .first()
            )
            if existing_user:
                raise exceptions.PhoneNumberAlreadyInUseException()
        return phone_number
