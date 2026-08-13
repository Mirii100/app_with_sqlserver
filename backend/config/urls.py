from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.authtoken import views as drf_views
from rest_framework import routers
from accounts.views import AccountViewSet, BillerViewSet, BeneficiaryViewSet
from chamas.views import ChamaViewSet, ChamaMembershipViewSet
from transactions.views import (
    TransactionViewSet,
    SavingsGoalViewSet,
    GoalTransactionViewSet,
    BudgetViewSet,
    UserLoanLimitViewSet,
    BillerCategoryViewSet,
    BillPaymentViewSet,
    ReportViewSet,
)
from core.views import signup, login, UserDetailView, SecuritySettingsViewSet, transfer_loan_to_main, transfer_to_chama_wallet, transfer_to_goal_wallet
from loans.views import LoanViewSet, LoanProductViewSet
from notifications.views import NotificationViewSet
from django.contrib import admin
router = routers.DefaultRouter()
router.register(r"accounts", AccountViewSet)
router.register(r"billers", BillerViewSet)
router.register(r"beneficiaries", BeneficiaryViewSet)
router.register(r"chamas", ChamaViewSet)
router.register(r"chama-memberships", ChamaMembershipViewSet)
router.register(r"transactions", TransactionViewSet)
router.register(r"savings-goals", SavingsGoalViewSet)
router.register(r"goal-transactions", GoalTransactionViewSet)
router.register(r"budgets", BudgetViewSet)
router.register(r"user-loan-limits", UserLoanLimitViewSet)
router.register(r"biller-categories", BillerCategoryViewSet)
router.register(r"bill-payments", BillPaymentViewSet, basename='bill-payment')
router.register(r"security-settings", SecuritySettingsViewSet)
router.register(r"loans", LoanViewSet)
router.register(r"loan-products", LoanProductViewSet)
router.register(r"notifications", NotificationViewSet)
router.register(r"reports", ReportViewSet, basename='report')

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/auth/signup/", signup),
    path("api/auth/login/", login),
    path("api/auth/token/", drf_views.obtain_auth_token),
    path("api/users/<int:pk>/", UserDetailView.as_view()),
    path("api/transfer-loan-to-main/", transfer_loan_to_main),
    path("api/transfer-to-chama-wallet/", transfer_to_chama_wallet),
    path("api/transfer-to-goal-wallet/", transfer_to_goal_wallet),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
