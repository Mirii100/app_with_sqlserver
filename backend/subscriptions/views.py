from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.models import Transaction

from .models import Subscription, SubscriptionWallet, UserSubscription
from .serializers import (
    SubscriptionSerializer,
    SubscriptionWalletSerializer,
    UserSubscriptionSerializer,
)

User = get_user_model()


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = UserSubscription.objects.select_related('user', 'subscription')
    serializer_class = UserSubscriptionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id, status='active')
        else:
            qs = qs.filter(user=self.request.user)
        return qs

    def create(self, request):
        user_id = request.data.get('user')
        subscription_id = request.data.get('subscription')

        if not user_id or not subscription_id:
            return Response({'error': 'user and subscription are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            subscription = Subscription.objects.get(id=subscription_id, active=True)
        except Subscription.DoesNotExist:
            return Response({'error': 'Subscription not found'}, status=status.HTTP_404_NOT_FOUND)

        obj, created = UserSubscription.objects.get_or_create(
            user=user,
            subscription=subscription,
            defaults={'status': 'active'},
        )
        if not created and obj.status != 'active':
            obj.status = 'active'
            obj.save()

        return Response(
            UserSubscriptionSerializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def cancel(self, request):
        user_id = request.query_params.get('user')
        subscription_id = request.query_params.get('subscription')

        if not user_id or not subscription_id:
            return Response({'error': 'user and subscription query params are required'}, status=status.HTTP_400_BAD_REQUEST)

        updated = UserSubscription.objects.filter(
            user_id=user_id,
            subscription_id=subscription_id,
            status='active',
        ).update(status='cancelled')

        if updated == 0:
            return Response({'error': 'Active subscription not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'status': 'success'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='available')
    def available(self, request):
        products = Subscription.objects.filter(active=True)
        return Response(SubscriptionSerializer(products, many=True).data)


class SubscriptionWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def _resolve_user(self, request):
        user_id = request.query_params.get('user')
        if user_id is not None:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return request.user
        return request.user

    def get(self, request):
        user = self._resolve_user(request)
        wallet, _ = SubscriptionWallet.objects.get_or_create(user=user)
        return Response(SubscriptionWalletSerializer(wallet).data)

    def post(self, request):
        user = self._resolve_user(request)

        amount_raw = request.data.get('amount')
        if amount_raw is None or amount_raw == '':
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(amount_raw))
        except (TypeError, ValueError, InvalidOperation):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'error': 'Amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        balance = Decimal(str(user.balance))
        if balance < amount:
            return Response({'error': 'Insufficient account balance'}, status=status.HTTP_400_BAD_REQUEST)

        wallet, _ = SubscriptionWallet.objects.get_or_create(user=user)

        with transaction.atomic():
            User.objects.filter(id=user.id).update(balance=F('balance') - amount)
            SubscriptionWallet.objects.filter(id=wallet.id).update(balance=F('balance') + amount)
            Transaction.objects.create(
                user=user,
                amount=amount,
                category='subscription_wallet_funding',
                type='withdrawal',
                description='Fund subscription wallet',
                date=timezone.now(),
            )

        wallet.refresh_from_db()
        user.refresh_from_db()
        return Response({
            'message': 'Subscription wallet funded',
            'amount': str(amount),
            'new_balance': str(user.balance),
            'wallet_balance': str(wallet.balance),
            'account_number': wallet.account_number,
        })
