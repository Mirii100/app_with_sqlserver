from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.authtoken import views as drf_views
from rest_framework import routers
from accounts.views import AccountViewSet, BillerViewSet
from chamas.views import ChamaViewSet, ChamaMembershipViewSet
from transactions.views import (
    TransactionViewSet,
    SavingsGoalViewSet,
    GoalTransactionViewSet,
)
from core.views import signup, login, UserDetailView
from loans.views import LoanViewSet, LoanProductViewSet
from django.contrib import admin
router = routers.DefaultRouter()
router.register(r"accounts", AccountViewSet)
router.register(r"billers", BillerViewSet)
router.register(r"chamas", ChamaViewSet)
router.register(r"chama-memberships", ChamaMembershipViewSet)
router.register(r"transactions", TransactionViewSet)
router.register(r"savings-goals", SavingsGoalViewSet)
router.register(r"goal-transactions", GoalTransactionViewSet)
router.register(r"loans", LoanViewSet)
router.register(r"loan-products", LoanProductViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/auth/signup/", signup),
    path("api/auth/login/", login),
    path("api/auth/token/", drf_views.obtain_auth_token),
    path("api/users/<int:pk>/", UserDetailView.as_view()),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )