from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.authtoken import views as drf_views
from rest_framework import routers
from accounts.views import AccountViewSet, CreditCardViewSet, DebitCardViewSet, UserCardSettingsViewSet
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
    ChequeBookRequestViewSet,
    StopPaymentOrderViewSet,
    FxViewSet,
    CryptoViewSet,
    ChequeViewSet,
)
from core.views import signup, login, UserDetailView, UserSecuritySettingsView, SecuritySettingsViewSet, PaymentQrCodeViewSet, transfer_loan_to_main, transfer_to_chama_wallet, transfer_to_goal_wallet, change_password, request_otp, verify_otp, email_statement, email_stock_statement, email_loan_statement
from core.admin_statements import send_statements_view
from loans.views import LoanViewSet, LoanProductViewSet
from notifications.views import NotificationViewSet
from subscriptions.views import SubscriptionViewSet, SubscriptionWalletView
from investments.views import InvestmentProductViewSet, InvestmentViewSet
from stocks.views import StockViewSet
from support.views import SupportTicketViewSet
from rewards.views import RewardViewSet
from insights.views import FinancialAdviceViewSet
from mpesa.views import STKPushViewSet, mpesa_callback
from django.contrib import admin
router = routers.DefaultRouter()
router.register(r"accounts", AccountViewSet)
router.register(r"credit-cards", CreditCardViewSet, basename='credit-card')
router.register(r"debit-cards", DebitCardViewSet, basename='debit-card')
router.register(r"card-settings", UserCardSettingsViewSet, basename='card-settings')
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
router.register(r"payment-qr", PaymentQrCodeViewSet, basename='payment-qr')
router.register(r"cheque-book-requests", ChequeBookRequestViewSet, basename='cheque-book-request')
router.register(r"stop-payment-orders", StopPaymentOrderViewSet, basename='stop-payment-order')
router.register(r"fx", FxViewSet, basename='fx')
router.register(r"crypto", CryptoViewSet, basename='crypto')
router.register(r"cheques", ChequeViewSet, basename='cheque')
router.register(r"loans", LoanViewSet)
router.register(r"loan-products", LoanProductViewSet)
router.register(r"notifications", NotificationViewSet)
router.register(r"reports", ReportViewSet, basename='report')
router.register(r"investment-products", InvestmentProductViewSet, basename='investment-product')
router.register(r"investments", InvestmentViewSet, basename='investment')
router.register(r"stocks", StockViewSet, basename='stock')
router.register(r"support-tickets", SupportTicketViewSet, basename='support-ticket')
router.register(r"rewards", RewardViewSet, basename='reward')
router.register(r"financial-advice", FinancialAdviceViewSet, basename='financial-advice')
router.register(r"mpesa", STKPushViewSet, basename='mpesa')

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/subscriptions/", SubscriptionViewSet.as_view({
        'get': 'list',
        'post': 'create',
        'delete': 'cancel',
    })),
    path("api/subscriptions/available/", SubscriptionViewSet.as_view({'get': 'available'})),
    path("api/subscription-wallet/", SubscriptionWalletView.as_view()),
    path("api/auth/signup/", signup),
    path("api/auth/login/", login),
    path("api/auth/change-password/", change_password),
    path("api/auth/otp/request/", request_otp),
    path("api/auth/otp/verify/", verify_otp),
    path("api/auth/token/", drf_views.obtain_auth_token),
    path("api/email-statement/", email_statement),
    path("api/email-stock-statement/", email_stock_statement),
    path("api/email-loan-statement/", email_loan_statement),
    path("api/users/<int:pk>/", UserDetailView.as_view()),
    path("api/users/<int:pk>/security/", UserSecuritySettingsView.as_view()),
    path("api/transfer-loan-to-main/", transfer_loan_to_main),
    path("api/transfer-to-chama-wallet/", transfer_to_chama_wallet),
    path("api/transfer-to-goal-wallet/", transfer_to_goal_wallet),
    path("api/mpesa/callback/", mpesa_callback, name="mpesa-callback"),
    path(
        "admin/send-statements/",
        admin.site.admin_view(send_statements_view),
        name="send_statements",
    ),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
