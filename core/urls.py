from rest_framework.routers import DefaultRouter
from django.urls import path
from . import views

app_name = "core"

router = DefaultRouter()
router.register(
    "deposit/cash-deposit",
    views.CashDepositViewSet,
    basename="cash-deposit",
)
router.register(
    "deposit/cheque",
    views.ChequeDepositViewSet,
    basename="cheque-deposit",
)
router.register(
    "deposit/ezwich",
    views.EZWICHDepositViewSet,
    basename="ezwich-deposit",
)
router.register(
    "deposit/mobile-money",
    views.MobileMoneyDepositViewSet,
    basename="mobile-money-deposit",
)

urlpatterns = [
    path("get-ticket/", views.GetTicketViewset.as_view(), name="get-ticket"),
    *router.urls,
]
