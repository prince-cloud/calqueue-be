from rest_framework.routers import DefaultRouter
from . import views

app_name = "core"

router = DefaultRouter()
router.register("tickets", views.TicketViewSet, basename="ticket")
router.register(
    "deposit/cash-deposit", views.CashDepositViewSet, basename="cash-deposit"
)
router.register("deposit/cheque", views.ChequeDepositViewSet, basename="cheque-deposit")
router.register("deposit/ezwich", views.EZWICHDepositViewSet, basename="ezwich-deposit")
router.register(
    "deposit/mobile-money",
    views.MobileMoneyDepositViewSet,
    basename="mobile-money-deposit",
)

urlpatterns = router.urls
