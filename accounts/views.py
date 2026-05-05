from . import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework import permissions as rest_permissions
from django.utils.translation import gettext_lazy as _
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from dj_rest_auth.utils import jwt_encode
from .models import CustomUser, UserID, UserAddress
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from helpers import exceptions
from django.db import transaction
from django.conf import settings
from dj_rest_auth.views import LoginView as DJREST_LoginView
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from django.core.cache import cache
from django.utils import timezone
from loguru import logger


class ProfileView(APIView):
    serializer_class = serializers.UserSerializer
    permission_classes = (rest_permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        serializer = serializers.UserSerializer(
            instance=user,
            many=False,
            context={"request": request},
        )
        return Response(data=serializer.data)


class SignUpViewset(CreateAPIView, DJREST_LoginView):
    """RegisterView takes a post method: Creates a user Account and sends
    AN OTP for user Activation
    """

    serializer_class = serializers.SignUpSerializer

    def get_response_data(self):
        if settings.ACCOUNT_EMAIL_VERIFICATION == "mandatory":
            return {
                "detail": _(
                    "Verification code has been sent to your e-mail or phone number."
                )
            }

    @transaction.atomic
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(request)
        # HACK :
        # code to get account token from dj_rest_auth
        self.serializer = serializer
        self.login()
        response = self.get_response()
        # send email to user
        # end dj_rest_auth hack
        return response


class CustomGoogleLoginView(GenericAPIView):
    """
    Custom Google OAuth2 Login View

    this view takes the authorization code and a request is being to exchange the
    id_token from google the id token si then being used to fetch the user data
    from gooogle.
    """

    serializer_class = serializers.CustomGoogleOauthLoginSerializer

    def post(self, request):
        serializer: serializers.GoogleOauthLoginSerializer = self.get_serializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        user_email = serializer.data["auth_code"]
        user = CustomUser.objects.get(email=user_email)
        access_token, refresh_token = jwt_encode(user)
        response = {
            "access": str(access_token),
            "refresh": str(refresh_token),
        }
        response["user"] = serializers.UserSerializer(
            instance=user,
            many=False,
            context=self.get_serializer_context(),
        ).data

        # try:
        #     send_account_creation_success_email(
        #         user_email=user.email,
        #         user_name=user.first_name,
        #     )
        #     send_new_account_notification(
        #         admin_email="acheampongprince227@gmail.com",
        #         user_name=user.fullname,
        #         user_email=user.email,
        #     )
        # except Exception as e:
        #     print("== error sending email: ", e)
        return Response(data=response, status=status.HTTP_200_OK)


class AppleLoginView(SocialLoginView):
    # if you want to use Authorization Code Grant, use this
    """
    This view allows users to use oauth login to Google and would be authenticated.
    """

    adapter_class = AppleOAuth2Adapter
    # callback_url = "CALLBACK_URL_ON_GOOGLE"  # TODO: fix this
    client_class = OAuth2Client


class ResetPasswordOtpView(CreateAPIView):
    """
    This view sends otp to users who wants to reset thier password.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.ResetPasswordOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _ = serializer.save()
        return Response({"message": "OTP successfully sent"}, status=status.HTTP_200_OK)


class ResetPasswordView(CreateAPIView):
    """
    This view sends otp to users who wants to reset thier password.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _ = serializer.save()
        return Response(
            {"message": "You have successfully reset your password."},
            status=status.HTTP_200_OK,
        )


class VerifyResetPasswordOTPView(CreateAPIView):
    """
    This view verifies the otp sent for password reset.
    """

    permission_classes = (rest_permissions.AllowAny,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")
    serializer_class = serializers.VerifyResetPasswordOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _ = serializer.save()
        return Response(
            {"message": "OTP successfully verified"},
            status=status.HTTP_200_OK,
        )


class SendPhoneNumberOTPViewset(CreateAPIView):
    serializer_class = serializers.SendPhoneNumberOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.send_email(request)
        return Response(
            {
                "success": True,
                "message": "OTP has been sent to your phone number",
            }
        )


class SendEmailOTPViewset(CreateAPIView):
    serializer_class = serializers.SendEmailOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.send_email(request)
        return Response(
            {
                "success": True,
                "message": "OTP has been sent to your email",
            }
        )


class VerifyOTPViewset(CreateAPIView):
    serializer_class = serializers.VerifyOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.verify_otp(request)
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class SetFCMTokenViewset(CreateAPIView):
    serializer_class = serializers.FCMAppTokenSerializer

    def post(self, request):
        if not request.user.is_authenticated:
            raise exceptions.NotAuthenticated()
        user: CustomUser = request.user
        serializer = serializers.FCMAppTokenSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["fcm_app_token"]
        user.fcm_app_token = token
        user.save()

        # Clear user profile cache since FCM token is part of user data
        profile_view = ProfileView()
        profile_view.clear_user_profile_cache(user.id)

        return Response(data=serializer.data)


class ProfileView(APIView):
    serializer_class = serializers.UserSerializer
    permission_classes = (rest_permissions.IsAuthenticated,)

    def get(self, request):
        """
        Retrieve user profile with caching.
        If the user profile has been retrieved before, return the cached object.
        """
        user = request.user
        logger.debug("Profile requested for user: {}", user.id)

        # Create a cache key using the user ID
        # cache_key = f"user_profile_{user.id}"

        # Try to get the cached response
        # cached_response = cache.get(cache_key)

        # if cached_response is not None:
        #     print(f"Returning cached user profile: {user.id}")
        #     return Response(cached_response, status=status.HTTP_200_OK)

        # If not cached, serialize the user data
        serializer = serializers.UserSerializer(
            instance=user,
            many=False,
            context={"request": request},
        )
        response_data = serializer.data

        # Cache the response for 30 minutes (1800 seconds)
        # cache.set(cache_key, response_data, 60 * 60 * 12)

        logger.debug("Returning user profile: {}", user.id)
        return Response(data=response_data, status=status.HTTP_200_OK)

    def clear_user_profile_cache(self, user_id):
        """
        Clear the cache for a specific user profile.
        """
        cache_key = f"user_profile_{user_id}"
        cache.delete(cache_key)
        logger.debug("Cleared cache for user profile: {}", user_id)


class UserIDView(APIView):
    """
    API endpoint to create or update user ID information.
    If the user doesn't have a UserID object, it will be created.
    If it exists, it will be updated (if can_update() returns True).
    """

    permission_classes = (rest_permissions.IsAuthenticated,)
    serializer_class = serializers.UserIDSerializer

    def post(self, request):
        """Create or update user ID information."""
        try:
            user_id = UserID.objects.get(user=request.user)
            # If object exists, check if update is allowed
            if not user_id.can_update():
                raise exceptions.UpdateNotAllowedException()
            serializer = self.serializer_class(user_id, data=request.data, partial=True)
        except UserID.DoesNotExist:
            # Create new object if it doesn't exist
            serializer = self.serializer_class(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        # Clear user profile cache since user identity is part of user data
        profile_view = ProfileView()
        profile_view.clear_user_profile_cache(request.user.id)

        return Response(serializer.data, status=status.HTTP_200_OK)


class UserAddressView(APIView):
    """
    API endpoint to create or update user address information.
    If the user doesn't have a UserAddress object, it will be created.
    If it exists, it will be updated (if can_update() returns True).
    """

    permission_classes = (rest_permissions.IsAuthenticated,)
    serializer_class = serializers.UserAddressSerializer

    def post(self, request):
        """Create or update user address information."""
        try:
            user_address = UserAddress.objects.get(user=request.user)
            # If object exists, check if update is allowed
            if not user_address.can_update():
                raise exceptions.UpdateNotAllowedException()
            serializer = self.serializer_class(
                user_address, data=request.data, partial=True
            )
        except UserAddress.DoesNotExist:
            # Create new object if it doesn't exist
            serializer = self.serializer_class(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        # Clear user profile cache since user address is part of user data
        profile_view = ProfileView()
        profile_view.clear_user_profile_cache(request.user.id)

        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfilePictureView(APIView):
    """
    API endpoint to update user profile picture and/or phone number.
    """

    permission_classes = (rest_permissions.IsAuthenticated,)
    serializer_class = serializers.ProfilePictureSerializer

    def post(self, request):
        """Update user profile picture and/or phone number."""
        user = request.user
        serializer = self.serializer_class(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Clear user profile cache since profile picture and phone number are part of user data
        profile_view = ProfileView()
        profile_view.clear_user_profile_cache(user.id)

        return Response(serializer.data, status=status.HTTP_200_OK)
