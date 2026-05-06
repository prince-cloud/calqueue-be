from django.urls import path
from . import views

app_name = "devices"

urlpatterns = [
    path("device/login/", views.DeviceLoginView.as_view(), name="device-login"),
    path("device/logout/", views.DeviceLogoutView.as_view(), name="device-logout"),
    path("device/token/refresh/", views.DeviceTokenRefreshView.as_view(), name="device-token-refresh"),
    path("device/me/", views.DeviceProfileView.as_view(), name="device-profile"),
]
