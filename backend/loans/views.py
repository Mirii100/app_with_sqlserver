from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Loan, LoanProduct
from .serializers import LoanSerializer, LoanProductSerializer
from django_filters.rest_framework import DjangoFilterBackend
from transactions.models import Transaction
from django.contrib.auth import get_user_model

User = get_user_model()


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user_id = request.data.get('user')
        if user_id:
            active_loan_count = Loan.objects.filter(
                user_id=user_id,
                status__in=['active', 'approved', 'pending']
            ).count()

            if active_loan_count >= 2:
                return Response({
                    'error': 'You cannot have more than 2 active loans at a time. Please repay existing loans first.',
                    'active_loan_count': active_loan_count,
                }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['post'], url_path='borrow')
    def borrow(self, request):
        user_id = request.data.get('user')
        amount = request.data.get('amount')
        interest_rate = request.data.get('interest_rate')
        loan_product_id = request.data.get('loan_product')

        if not all([user_id, amount, interest_rate]):
            return Response({'error': 'user, amount, and interest_rate are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        active_loan_count = Loan.objects.filter(
            user=user,
            status__in=['active', 'approved', 'pending']
        ).count()

        if active_loan_count >= 2:
            return Response({
                'error': 'You cannot have more than 2 active loans at a time. Please repay existing loans first.',
                'active_loan_count': active_loan_count,
            }, status=status.HTTP_400_BAD_REQUEST)

        amount_value = Decimal(str(amount))
        interest_value = Decimal(str(interest_rate))

        loan_product = None
        if loan_product_id:
            try:
                loan_product = LoanProduct.objects.get(id=loan_product_id)
            except LoanProduct.DoesNotExist:
                pass

        with transaction.atomic():
            User.objects.filter(id=user.id).update(balance=F('balance') + amount_value)

            Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='loan_disbursement',
                type='deposit',
                description=f'Loan disbursement #{loan_product_id or ""}',
                date=timezone.now(),
            )

            loan = Loan.objects.create(
                user=user,
                loan_product=loan_product,
                amount=amount_value,
                approved_amount=amount_value,
                outstanding_amount=amount_value,
                interest_rate=interest_value,
                status='active',
                purpose=request.data.get('purpose', ''),
            )

        user.refresh_from_db()

        return Response({
            'status': 'success',
            'loan_id': loan.id,
            'amount': str(loan.amount),
            'outstanding_amount': str(loan.outstanding_amount),
            'new_balance': str(user.balance),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='repay')
    def repay(self, request, pk=None):
        loan = self.get_object()
        user = loan.user
        amount = request.data.get('amount')
        is_partial = request.data.get('partial', False)

        if not amount:
            return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        amount_value = Decimal(str(amount))

        if loan.status not in ['active', 'pending', 'approved']:
            return Response({'error': f'Loan cannot be repaid in current status: {loan.status}'}, status=status.HTTP_400_BAD_REQUEST)

        if amount_value > loan.outstanding_amount:
            amount_value = loan.outstanding_amount

        remaining = loan.outstanding_amount - amount_value

        with transaction.atomic():
            User.objects.filter(id=user.id).update(balance=F('balance') - amount_value)

            Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='loan_repayment',
                type='withdrawal',
                description=f'Loan repayment - Loan #{loan.id}',
                date=timezone.now(),
            )

            if remaining <= 0:
                loan.outstanding_amount = 0
                loan.status = 'completed'
            else:
                loan.outstanding_amount = remaining
            loan.save()

        user.refresh_from_db()
        loan.refresh_from_db()

        return Response({
            'status': 'success',
            'repayment_amount': str(amount_value),
            'remaining_balance': str(loan.outstanding_amount),
            'loan_status': loan.status,
            'user_balance': str(user.balance),
            'is_partial': is_partial,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='user-summary')
    def user_summary(self, request):
        user_id = request.query_params.get('user')
        if not user_id:
            return Response({'error': 'user parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        loans = Loan.objects.filter(user=user)
        loan_summary = []
        active_count = 0

        for loan in loans:
            loan_summary.append({
                'id': loan.id,
                'amount': str(loan.amount),
                'approved_amount': str(loan.approved_amount),
                'outstanding_amount': str(loan.outstanding_amount),
                'interest_rate': str(loan.interest_rate),
                'duration_months': loan.duration_months,
                'status': loan.status,
                'purpose': loan.purpose,
                'created_at': loan.created_at.isoformat(),
            })
            if loan.status in ['active', 'approved', 'pending']:
                active_count += 1

        can_borrow = active_count < 2

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'phone_number': user.phone_number,
                'account_number': user.account_number,
                'balance': str(user.balance),
                'loan_limit': str(user.loan_limit),
                'loan_used': str(user.loan_used),
            },
            'loan_summary': loan_summary,
            'active_loan_count': active_count,
            'can_borrow': can_borrow,
        })


class LoanProductViewSet(viewsets.ModelViewSet):
    queryset = LoanProduct.objects.all()
    serializer_class = LoanProductSerializer
    permission_classes = [IsAuthenticated]
