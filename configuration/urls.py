from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "configuration"

router = DefaultRouter()
router.register("main-services", views.MainServiceViewSet, basename="main-service")
router.register("services", views.ServiceViewSet, basename="service")

urlpatterns = [
    path("device/login/", views.DeviceLoginView.as_view(), name="device-login"),
    path("device/logout/", views.DeviceLogoutView.as_view(), name="device-logout"),
    path("device/token/refresh/", views.DeviceTokenRefreshView.as_view(), name="device-token-refresh"),
    path("device/me/", views.DeviceProfileView.as_view(), name="device-profile"),
    *router.urls,
]
