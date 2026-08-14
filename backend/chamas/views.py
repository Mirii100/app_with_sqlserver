from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.contrib.auth import get_user_model
from stocks.fees import CHAMA_FLAT_FEE, _money, record_charges
from .models import Chama, ChamaMembership
from .serializers import ChamaSerializer, ChamaMembershipSerializer
from transactions.models import Transaction

User = get_user_model()


class ChamaViewSet(viewsets.ModelViewSet):
    queryset = Chama.objects.all()
    serializer_class = ChamaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        member_id = self.request.query_params.get('member')
        if member_id:
            qs = qs.filter(memberships__user_id=member_id)
        return qs

    def perform_create(self, serializer):
        chama = serializer.save()
        ChamaMembership.objects.get_or_create(
            chama=chama,
            user_id=chama.admin_id,
            defaults={'role': 'admin'},
        )

    def _get_membership(self, chama, user):
        return ChamaMembership.objects.filter(chama=chama, user=user).first()

    @action(detail=False, methods=['get'], url_path='my-chamas')
    def my_chamas(self, request):
        """Chamas the authenticated (or ?user=) user is a member of, with their contribution."""
        user_id = request.query_params.get('user')
        if not user_id:
            if not request.user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            user_id = request.user.id

        memberships = ChamaMembership.objects.filter(user_id=user_id).select_related('chama').order_by('-joined_at')
        results = []
        for membership in memberships:
            chama = membership.chama
            data = ChamaSerializer(chama, context={'request': request}).data
            data['my_contribution'] = str(membership.contributed_amount)
            data['my_role'] = membership.role
            data['membership_id'] = membership.id
            results.append(data)

        return Response(results)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        chama = self.get_object()
        user_id = request.data.get('user')
        if not user_id:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check existing memberships
        membership_count = ChamaMembership.objects.filter(user_id=user_id).count()
        if membership_count >= 2:
             return Response({'error': 'You cannot join more than 2 chamas.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Mandatory chama account fee of KSh 200, deducted directly from the
        # member's chama wallet balance.
        if user.chama_wallet_balance < CHAMA_FLAT_FEE:
            return Response(
                {'error': f'Chama account fee of KSh {CHAMA_FLAT_FEE} is required to join. '
                          f'Please fund your chama wallet.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            membership, created = ChamaMembership.objects.get_or_create(chama=chama, user=user)

            if created:
                chama.member_count += 1
                chama.save()

                fee_txn = Transaction.objects.create(
                    user=user,
                    amount=CHAMA_FLAT_FEE,
                    category='chama_join_fee',
                    type='withdrawal',
                    description=f'Chama join fee for {chama.name}',
                    date=timezone.now(),
                )
                User.objects.filter(id=user.id).update(
                    chama_wallet_balance=F('chama_wallet_balance') - CHAMA_FLAT_FEE,
                )
                user.refresh_from_db()
                record_charges(
                    user, 'chama_join_fee', 'chama_join', fee_txn,
                    CHAMA_FLAT_FEE, account_number=user.account_number,
                    flat_fee=CHAMA_FLAT_FEE,
                )

        if created:
            return Response({
                'status': 'Joined chama',
                'chama_fee': str(CHAMA_FLAT_FEE),
                'chama_wallet': str(user.chama_wallet_balance),
            }, status=status.HTTP_201_CREATED)
        return Response({'status': 'Already a member'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='contribute')
    def contribute(self, request, pk=None):
        chama = self.get_object()
        user_id = request.data.get('user')
        amount = request.data.get('amount')

        if not all([user_id, amount]):
            return Response({'error': 'user and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        if amount_value <= 0:
            return Response({'error': 'Amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        # Mandatory KSh 200 chama account fee is deducted from the member's
        # chama wallet on every contribution. The contribution itself credits
        # the chama wallet, so the post-contribution balance must cover the fee.
        if (user.chama_wallet_balance + amount_value) < CHAMA_FLAT_FEE:
            return Response(
                {'error': f'A mandatory chama account fee of KSh {CHAMA_FLAT_FEE} is '
                          'applied to every contribution. Contribution amount must be '
                          'at least KSh 200.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership = ChamaMembership.objects.filter(chama=chama, user=user).first()
        if not membership:
            return Response({'error': 'You must join the chama before contributing'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Move the contribution amount from the main balance to the chama
            # wallet and to the chama's total pool.
            User.objects.filter(id=user.id).update(
                balance=F('balance') - amount_value,
                chama_wallet_balance=F('chama_wallet_balance') + amount_value,
            )

            pool_txn = Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='chama_contribution',
                type='withdrawal',
                description=f'Chama contribution to {chama.name}',
                date=timezone.now(),
            )

            Chama.objects.filter(id=chama.id).update(
                total_pool_balance=F('total_pool_balance') + amount_value
            )

            ChamaMembership.objects.filter(id=membership.id).update(
                contributed_amount=F('contributed_amount') + amount_value
            )

            # Mandatory chama account fee — deducted from the member's chama
            # wallet and recorded as AlexiaFinancials company revenue.
            fee_txn = Transaction.objects.create(
                user=user,
                amount=CHAMA_FLAT_FEE,
                category='chama_fee',
                type='withdrawal',
                description=f'Chama account fee for contribution to {chama.name}',
                date=timezone.now(),
            )
            User.objects.filter(id=user.id).update(
                chama_wallet_balance=F('chama_wallet_balance') - CHAMA_FLAT_FEE,
            )
            user.refresh_from_db()
            record_charges(
                user, 'chama_fee', 'chama_contribution', fee_txn,
                CHAMA_FLAT_FEE,
                account_number=user.account_number,
                flat_fee=CHAMA_FLAT_FEE,
            )

        user.refresh_from_db()
        chama.refresh_from_db()
        membership.refresh_from_db()

        return Response({
            'status': 'success',
            'amount': str(amount_value),
            'chama_fee': str(CHAMA_FLAT_FEE),
            'chama_name': chama.name,
            'new_pool_balance': str(chama.total_pool_balance),
            'user_balance': str(user.balance),
            'chama_wallet': str(user.chama_wallet_balance),
            'my_contribution': str(membership.contributed_amount),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        """Move funds from a chama's pool back to the member's main account."""
        chama = self.get_object()
        user_id = request.data.get('user')
        amount = request.data.get('amount')

        if not all([user_id, amount]):
            return Response({'error': 'user and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        if amount_value <= 0:
            return Response({'error': 'Amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        membership = ChamaMembership.objects.filter(chama=chama, user=user).first()
        if not membership:
            return Response({'error': 'You must be a member of this chama'}, status=status.HTTP_400_BAD_REQUEST)

        if membership.contributed_amount < amount_value:
            return Response(
                {'error': 'Amount exceeds your total contribution to this chama'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if chama.total_pool_balance < amount_value:
            return Response({'error': 'Chama pool has insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            User.objects.filter(id=user.id).update(
                balance=F('balance') + amount_value,
                chama_wallet_balance=F('chama_wallet_balance') - amount_value,
            )

            Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='chama_withdrawal',
                type='deposit',
                description=f'Withdrawal from {chama.name}',
                date=timezone.now(),
            )

            Chama.objects.filter(id=chama.id).update(
                total_pool_balance=F('total_pool_balance') - amount_value
            )

            ChamaMembership.objects.filter(id=membership.id).update(
                contributed_amount=F('contributed_amount') - amount_value
            )

        user.refresh_from_db()
        chama.refresh_from_db()
        membership.refresh_from_db()

        return Response({
            'status': 'success',
            'amount': str(amount_value),
            'chama_name': chama.name,
            'new_pool_balance': str(chama.total_pool_balance),
            'user_balance': str(user.balance),
            'chama_wallet': str(user.chama_wallet_balance),
            'my_contribution': str(membership.contributed_amount),
        }, status=status.HTTP_200_OK)


class ChamaMembershipViewSet(viewsets.ModelViewSet):
    queryset = ChamaMembership.objects.all()
    serializer_class = ChamaMembershipSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        chama_id = self.request.query_params.get('chama')
        user_id = self.request.query_params.get('user')
        if chama_id:
            qs = qs.filter(chama_id=chama_id)
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs
