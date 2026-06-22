from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "configuration"

router = DefaultRouter()
router.register("branches", views.BranchViewSet, basename="branch")
router.register("devices", views.DeviceViewSet, basename="device")
router.register("main-services", views.MainServiceViewSet, basename="main-service")
router.register("services", views.ServiceViewSet, basename="service")
router.register("counters", views.CounterViewSet, basename="counter")
router.register("other-banks", views.OtherBankViewSet, basename="other-bank")
router.register("other-bank-branches", views.OtherBankBranchViewSet, basename="other-bank-branch")

urlpatterns = [
    # Mobile customer-app endpoints (additive, read-only)
    path("mobile/branches/nearest/", views.NearestBranchView.as_view(), name="mobile-nearest-branch"),
    path("mobile/services/", views.MobileServiceCatalogueView.as_view(), name="mobile-services"),
    path("device/login/", views.DeviceLoginView.as_view(), name="device-login"),
    path("device/logout/", views.DeviceLogoutView.as_view(), name="device-logout"),
    path("device/token/refresh/", views.DeviceTokenRefreshView.as_view(), name="device-token-refresh"),
    path("device/me/", views.DeviceProfileView.as_view(), name="device-profile"),
    path("voice-config/", views.SystemVoiceConfigView.as_view(), name="system-voice-config"),
    path("voice-config/preview/", views.VoicePreviewView.as_view(), name="voice-config-preview"),
    path("branches/<uuid:branch_uuid>/voice-config/", views.BranchVoiceConfigView.as_view(), name="branch-voice-config"),
    path("branches/<uuid:branch_uuid>/tv-config/", views.BranchTVConfigView.as_view(), name="branch-tv-config"),
    path("branches/<uuid:branch_uuid>/tv-config/ads/", views.BranchTVAdsView.as_view(), name="branch-tv-ads"),
    path("branches/<uuid:branch_uuid>/tv-config/ads/<int:ad_id>/", views.BranchTVAdsView.as_view(), name="branch-tv-ad-detail"),
    *router.urls,
]
