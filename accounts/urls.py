from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views
from dj_rest_auth.views import LoginView
from dj_rest_auth.views import PasswordChangeView

app_name = "accounts"

router = DefaultRouter()


urlpatterns = [
    path("signup/", views.SignUpViewset.as_view(), name="signup"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/user-id/", views.UserIDView.as_view(), name="user-id"),
    path("profile/user-address/", views.UserAddressView.as_view(), name="user-address"),
    path("profile/update/", views.ProfilePictureView.as_view(), name="profile-update"),
    path(
        "signup/verify-otp/",
        views.VerifyOTPViewset.as_view(),
        name="signup-verify-otp",
    ),
    path(
        "signup/send-phone-number-otp/",
        views.SendPhoneNumberOTPViewset.as_view(),
        name="signup-send-otp",
    ),
    path(
        "signup/send-email-otp/",
        views.SendEmailOTPViewset.as_view(),
        name="signup-send-email-otp",
    ),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # oauth for google and github
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path(
        "password/reset-otp/",
        views.ResetPasswordOtpView.as_view(),
        name="password-reset-otp",
    ),
    path(
        "password/verify-reset-otp/",
        views.VerifyResetPasswordOTPView.as_view(),
        name="verify-password-reset-otp",
    ),
    path("password/reset/", views.ResetPasswordView.as_view(), name="password-reset"),
]

urlpatterns += router.urls
