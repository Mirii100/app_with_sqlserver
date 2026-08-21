from decimal import Decimal, InvalidOperation
import json
import random
import string
from datetime import timedelta, datetime
from django.db import transaction
from django.db.models import F, Sum, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from accounts.models import Account, Biller, generate_biller_account_number

from chamas.models import Chama, ChamaMembership
from loans.models import Loan
from stocks.fees import compute_tiered_charges, record_charges, _money
from .models import (BillerCategory, Transaction, SavingsGoal, GoalTransaction,
                     Budget, UserLoanLimit, CHEQUE_BOOK_FEE, CHEQUE_COURIER_FEE,
                     STOP_PAYMENT_FEE, FX_FEE, CRYPTO_TRADE_FEE_RATE,
                     ChequeBookRequest, StopPaymentOrder, FxRate, CurrencyWallet,
                     CryptoAsset, CryptoHolding, Cheque)
from .serializers import (BillerCategorySerializer, TransactionSerializer,
                          SavingsGoalSerializer, GoalTransactionSerializer,
                          BudgetSerializer, UserLoanLimitSerializer,
                          ChequeBookRequestSerializer, StopPaymentOrderSerializer,
                          FxRateSerializer, CryptoAssetSerializer,
                          ChequeSerializer)


def models_decimal(value):
    return Decimal(str(value)).quantize(Decimal('0.01'))

User = get_user_model()

SPENDING_BUCKETS = {
    'cash': 'Cash withdrawal',
    'withdraw': 'Cash withdrawal',
    'transfer': 'Transfers',
    'sent': 'Transfers',
    'loan_repay': 'Loan repayment',
    'repay': 'Loan repayment',
    'savings_goal_fund': 'Savings',
    'chama_contribution': 'Chama',
}


def _spending_bucket(category):
    """Maps a transaction category to a friendly spending bucket."""
    c = (category or '').lower()
    food_keys = ('food', 'grocery', 'restaurant', 'supermarket', 'meal', 'eats', 'drink')
    transport_keys = ('transport', 'fuel', 'petrol', 'matatu', 'uber', 'taxi', 'bus', 'fare', 'flight', 'train')
    airtime_keys = ('airtime', 'data', 'internet', 'bundle', 'mobile', 'call', 'recharge')
    for key in food_keys:
        if key in c:
            return 'Food'
    for key in transport_keys:
        if key in c:
            return 'Transport'
    for key in airtime_keys:
        if key in c:
            return 'Airtime'
    for key, label in SPENDING_BUCKETS.items():
        if key in c:
            return label
    return 'Other'

class BillPaymentViewSet(viewsets.ViewSet):
    def create(self, request):
        user_id = request.data.get('user')
        amount = request.data.get('amount')
        category = request.data.get('category')
        description = request.data.get('description')
        biller_id = request.data.get('biller')

        if not all([user_id, amount, category, biller_id]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            biller = Biller.objects.get(id=biller_id)
        except (Biller.DoesNotExist, ValueError):
            return Response({'error': 'Biller not found'}, status=status.HTTP_404_NOT_FOUND)

        if not biller.account_number:
            biller.account_number = generate_biller_account_number()
            biller.save(update_fields=['account_number'])

        try:
            account = Account.objects.get(user_id=user_id)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        if amount_value <= 0:
            return Response({'error': 'Amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(amount_value)
        total_deduction = _money(amount_value + broker_fee + gov_tax)

        if account.user.balance < total_deduction:
            return Response(
                {'error': f'Insufficient balance. KSh {_money(broker_fee + gov_tax)} in charges '
                          'apply.',
                 'broker_fee': str(broker_fee),
                 'government_tax': str(gov_tax),
                 'total_charges': str(_money(broker_fee + gov_tax))},
                status=status.HTTP_400_BAD_REQUEST,
            )

        biller_name = biller.title or biller.name or str(biller.id)
        if not description:
            description = f"Payment to {biller_name}"
        if biller.account_number and 'Acc' not in description:
            description = f"{description} • Acc {biller.account_number}"

        with transaction.atomic():
            User.objects.filter(id=account.user.id).update(
                balance=F('balance') - total_deduction
            )

            biller.balance += amount_value
            biller.save(update_fields=['balance'])

            txn = Transaction.objects.create(
                user=account.user,
                amount=total_deduction,
                broker_fee=broker_fee,
                government_tax=gov_tax,
                category=category,
                type='withdrawal',
                description=f"{description} (KSh {amount_value} + charges KSh {_money(broker_fee + gov_tax)})",
                date=timezone.now(),
            )

            record_charges(
                account.user, 'bill_payment', 'bill_payment', txn, amount_value,
                account_number=account.user.account_number,
                broker_fee=broker_fee, gov_tax=gov_tax,
                broker_rate=broker_rate, tax_rate=tax_rate,
            )

        return Response({
            'status': 'success',
            'biller': biller_name,
            'account_number': biller.account_number,
            'biller_balance': str(biller.balance),
            'amount': str(amount_value),
            'broker_fee': str(broker_fee),
            'government_tax': str(gov_tax),
            'total_charges': str(_money(broker_fee + gov_tax)),
        }, status=status.HTTP_201_CREATED)

class BillerCategoryViewSet(viewsets.ModelViewSet):
    queryset = BillerCategory.objects.all()
    serializer_class = BillerCategorySerializer

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related('user')
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id is not None:
            return qs.filter(user_id=user_id)
        return qs.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='deposit')
    def deposit(self, request):
        user_id = request.data.get('user')
        amount = request.data.get('amount')

        if not all([user_id, amount]):
            return Response({'error': 'user and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        description = request.data.get('description', 'Deposit')

        with transaction.atomic():
            txn = Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='deposit',
                type='deposit',
                description=description,
                date=timezone.now(),
            )

            User.objects.filter(id=user.id).update(balance=F('balance') + amount_value)

            from rewards.points import award_points
            award_points(
                user,
                'deposit',
                key=f'deposit:{txn.reference}',
                description=f'Deposit of KSh {amount_value}',
            )

        user.refresh_from_db()

        return Response({
            'status': 'success',
            'reference': txn.reference,
            'new_balance': str(user.balance),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='withdraw')
    def withdraw(self, request):
        user_id = request.data.get('user')
        amount = request.data.get('amount')

        if not all([user_id, amount]):
            return Response({'error': 'user and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(amount_value)
        total_deduction = _money(amount_value + broker_fee + gov_tax)

        if user.balance < total_deduction:
            return Response(
                {'error': f'Insufficient balance. KSh {_money(broker_fee + gov_tax)} in charges '
                          'apply to this withdrawal.',
                 'broker_fee': str(broker_fee),
                 'government_tax': str(gov_tax),
                 'total_charges': str(_money(broker_fee + gov_tax))},
                status=status.HTTP_400_BAD_REQUEST,
            )

        description = request.data.get('description', 'Withdrawal')

        with transaction.atomic():
            txn = Transaction.objects.create(
                user=user,
                amount=total_deduction,
                broker_fee=broker_fee,
                government_tax=gov_tax,
                category='withdrawal',
                type='withdrawal',
                description=f"{description} (KSh {amount_value} + charges KSh {_money(broker_fee + gov_tax)})",
                date=timezone.now(),
            )

            User.objects.filter(id=user.id).update(balance=F('balance') - total_deduction)

            record_charges(
                user, 'withdrawal', 'withdrawal', txn, amount_value,
                account_number=user.account_number,
                broker_fee=broker_fee, gov_tax=gov_tax,
                broker_rate=broker_rate, tax_rate=tax_rate,
            )

        user.refresh_from_db()

        return Response({
            'status': 'success',
            'reference': txn.reference,
            'new_balance': str(user.balance),
            'broker_fee': str(broker_fee),
            'government_tax': str(gov_tax),
            'total_charges': str(_money(broker_fee + gov_tax)),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='transfer')
    def transfer(self, request):
        sender_id = request.data.get('sender')
        recipient_phone = request.data.get('recipient_phone')
        amount = request.data.get('amount')

        if not all([sender_id, recipient_phone, amount]):
            return Response({'error': 'sender, recipient_phone, and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sender = User.objects.get(id=sender_id)
        except User.DoesNotExist:
            return Response({'error': 'Sender not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            recipient = User.objects.get(phone_number=recipient_phone)
        except User.DoesNotExist:
            return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(amount_value)
        total_deduction = _money(amount_value + broker_fee + gov_tax)

        if sender.balance < total_deduction:
            return Response(
                {'error': f'Insufficient balance. KSh {broker_fee + gov_tax} in charges '
                          'apply to this transfer.',
                 'broker_fee': str(broker_fee),
                 'government_tax': str(gov_tax),
                 'total_charges': str(_money(broker_fee + gov_tax))},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            User.objects.filter(id=sender.id).update(balance=F('balance') - total_deduction)
            User.objects.filter(id=recipient.id).update(balance=F('balance') + amount_value)

            sender_txn = Transaction.objects.create(
                    user=sender,
                    amount=total_deduction,
                    broker_fee=broker_fee,
                    government_tax=gov_tax,
                    category='transfer_out',
                    type='withdrawal',
                    description=f"Transfer to {recipient.phone_number} "
                                f"(KSh {amount_value} + charges KSh {_money(broker_fee + gov_tax)})",
                    date=timezone.now(),
            )

            Transaction.objects.create(
                user=recipient,
                amount=amount_value,
                category='transfer_in',
                type='deposit',
                description=f"Transfer from {sender.phone_number}",
                date=timezone.now(),
            )

            record_charges(
                sender, 'transfer', 'transfer', sender_txn, amount_value,
                account_number=sender.account_number,
                broker_fee=broker_fee, gov_tax=gov_tax,
                broker_rate=broker_rate, tax_rate=tax_rate,
            )

        sender.refresh_from_db()
        recipient.refresh_from_db()

        return Response({
            'status': 'success',
            'reference': sender_txn.reference,
            'amount': str(amount_value),
            'broker_fee': str(broker_fee),
            'government_tax': str(gov_tax),
            'total_charges': str(_money(broker_fee + gov_tax)),
            'total_deduction': str(total_deduction),
            'sender_balance': str(sender.balance),
            'recipient_balance': str(recipient.balance),
        }, status=status.HTTP_201_CREATED)

class SavingsGoalViewSet(viewsets.ModelViewSet):
    queryset = SavingsGoal.objects.all()
    serializer_class = SavingsGoalSerializer

    def get_queryset(self):
        # Always scope to the authenticated user. Never trust a `user`
        # query param — that would let anyone read another user's goals.
        return SavingsGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='fund')
    def fund(self, request, pk=None):
        goal = self.get_object()
        user = request.user
        amount = request.data.get('amount')

        if not amount:
            return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_value = Decimal(str(amount))
        except (TypeError, ValueError, InvalidOperation):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount_value <= 0:
            return Response({'error': 'Amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(amount_value)
        total_deduction = _money(amount_value + broker_fee + gov_tax)

        if user.balance < total_deduction:
            return Response(
                {'error': f'Insufficient balance. KSh {_money(broker_fee + gov_tax)} in charges '
                          'apply.',
                 'broker_fee': str(broker_fee),
                 'government_tax': str(gov_tax),
                 'total_charges': str(_money(broker_fee + gov_tax))},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            User.objects.filter(id=user.id).update(
                balance=F('balance') - total_deduction,
                goal_wallet_balance=F('goal_wallet_balance') + amount_value,
            )

            txn = Transaction.objects.create(
                user=user,
                amount=total_deduction,
                broker_fee=broker_fee,
                government_tax=gov_tax,
                category='savings_goal_funding',
                type='withdrawal',
                description=f'Funding goal: {goal.title} (KSh {amount_value} + charges KSh {_money(broker_fee + gov_tax)})',
                date=timezone.now(),
            )

            SavingsGoal.objects.filter(id=goal.id).update(
                saved_amount=F('saved_amount') + amount_value
            )

            from rewards.points import award_points
            award_points(
                user,
                'goal_saving',
                key=f'goal_fund:{txn.reference}',
                description=f'Saved KSh {amount_value} toward "{goal.title}"',
            )

            record_charges(
                user, 'goal_funding', 'goal_funding', txn, amount_value,
                account_number=user.account_number,
                broker_fee=broker_fee, gov_tax=gov_tax,
                broker_rate=broker_rate, tax_rate=tax_rate,
            )

        user.refresh_from_db()
        goal.refresh_from_db()

        return Response({
            'status': 'success',
            'amount': str(amount_value),
            'goal_title': goal.title,
            'new_saved_amount': str(goal.saved_amount),
            'user_balance': str(user.balance),
            'goal_wallet_balance': str(user.goal_wallet_balance),
            'broker_fee': str(broker_fee),
            'government_tax': str(gov_tax),
            'total_charges': str(_money(broker_fee + gov_tax)),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        goal = self.get_object()
        user = request.user
        amount = request.data.get('amount')

        if not amount:
            return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_value = Decimal(str(amount))
        except (TypeError, ValueError, InvalidOperation):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount_value <= 0:
            return Response({'error': 'Amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        if goal.saved_amount < amount_value:
            return Response({'error': 'Insufficient goal savings'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            User.objects.filter(id=user.id).update(
                balance=F('balance') + amount_value,
                goal_wallet_balance=F('goal_wallet_balance') - amount_value,
            )

            Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='savings_goal_withdrawal',
                type='deposit',
                description=f'Withdrawal from goal: {goal.title}',
                date=timezone.now(),
            )

            SavingsGoal.objects.filter(id=goal.id).update(
                saved_amount=F('saved_amount') - amount_value
            )

        user.refresh_from_db()
        goal.refresh_from_db()

        return Response({
            'status': 'success',
            'amount': str(amount_value),
            'goal_title': goal.title,
            'new_saved_amount': str(goal.saved_amount),
            'user_balance': str(user.balance),
            'goal_wallet_balance': str(user.goal_wallet_balance),
        }, status=status.HTTP_200_OK)


class GoalTransactionViewSet(viewsets.ModelViewSet):
    queryset = GoalTransaction.objects.all()
    serializer_class = GoalTransactionSerializer

    def get_queryset(self):
        return GoalTransaction.objects.filter(user=self.request.user)

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='spending-analysis')
    def spending_analysis(self, request):
        """Real spending for the current and previous month, computed from the
        Transaction table for the authenticated user (not from stored snapshots)."""
        user = request.user

        now = timezone.now()
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_end = (current_start + timedelta(days=32)).replace(day=1)
        previous_start = (current_start - timedelta(days=1)).replace(day=1)
        previous_end = current_start

        def compute_spending(start, end):
            rows = (
                Transaction.objects.filter(
                    user=user,
                    type='withdrawal',
                    date__gte=start,
                    date__lt=end,
                )
                .values('category')
                .annotate(total=Sum('amount'))
            )
            buckets = {}
            for row in rows:
                label = _spending_bucket(row['category'])
                buckets[label] = buckets.get(label, Decimal('0')) + row['total']
            return {k: str(v) for k, v in buckets.items()}

        def budget_limits_for(start):
            budget = Budget.objects.filter(user=user, month=start.strftime('%Y-%m')).first()
            if not budget:
                return {}
            value = budget.budget_limits
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (TypeError, ValueError):
                    return {}
            return value if isinstance(value, dict) else {}

        return Response({
            'current_month': {
                'month': current_start.strftime('%Y-%m'),
                'categories': compute_spending(current_start, current_end),
                'budget_limits': budget_limits_for(current_start),
            },
            'previous_month': {
                'month': previous_start.strftime('%Y-%m'),
                'categories': compute_spending(previous_start, previous_end),
                'budget_limits': budget_limits_for(previous_start),
            },
        })

class UserLoanLimitViewSet(viewsets.ModelViewSet):
    queryset = UserLoanLimit.objects.all()
    serializer_class = UserLoanLimitSerializer


class ReportViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='loan-report')
    def loan_report(self, request):
        total_loans = Loan.objects.count()
        active_loans = Loan.objects.filter(status='active').count()
        pending_loans = Loan.objects.filter(status='pending').count()
        approved_loans = Loan.objects.filter(status='approved').count()
        rejected_loans = Loan.objects.filter(status='rejected').count()
        completed_loans = Loan.objects.filter(status='completed').count()

        total_loaned = Loan.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_outstanding = Loan.objects.aggregate(total=Sum('outstanding_amount'))['total'] or Decimal('0.00')

        recent_loans = Loan.objects.select_related('user', 'loan_product').order_by('-created_at')[:10]
        recent_loans_data = [
            {
                'id': loan.id,
                'user': loan.user.username,
                'user_email': loan.user.email,
                'loan_product': loan.loan_product.name if loan.loan_product else None,
                'amount': str(loan.amount),
                'approved_amount': str(loan.approved_amount),
                'outstanding_amount': str(loan.outstanding_amount),
                'interest_rate': str(loan.interest_rate),
                'duration_months': loan.duration_months,
                'status': loan.status,
                'purpose': loan.purpose,
                'created_at': loan.created_at.isoformat(),
            }
            for loan in recent_loans
        ]

        return Response({
            'summary': {
                'total_loans': total_loans,
                'active_loans': active_loans,
                'pending_loans': pending_loans,
                'approved_loans': approved_loans,
                'rejected_loans': rejected_loans,
                'completed_loans': completed_loans,
                'total_loaned': str(total_loaned),
                'total_outstanding': str(total_outstanding),
            },
            'recent_loans': recent_loans_data,
        })

    @action(detail=False, methods=['get'], url_path='account-members')
    def account_members_report(self, request):
        total_users = User.objects.count()
        total_accounts = Account.objects.count()
        active_accounts = Account.objects.filter(status='active').count()

        total_balance = User.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')
        total_loan_limit = User.objects.aggregate(total=Sum('loan_limit'))['total'] or Decimal('0.00')
        total_loan_used = User.objects.aggregate(total=Sum('loan_used'))['total'] or Decimal('0.00')

        user_accounts = User.objects.select_related('account').order_by('-date_joined')[:20]
        members_data = [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'phone_number': user.phone_number,
                'account_number': user.account_number,
                'balance': str(user.balance),
                'loan_limit': str(user.loan_limit),
                'loan_used': str(user.loan_used),
                'date_joined': user.date_joined.isoformat(),
            }
            for user in user_accounts
        ]

        return Response({
            'summary': {
                'total_users': total_users,
                'total_accounts': total_accounts,
                'active_accounts': active_accounts,
                'total_balance': str(total_balance),
                'total_loan_limit': str(total_loan_limit),
                'total_loan_used': str(total_loan_used),
            },
            'members': members_data,
        })

    @action(detail=False, methods=['get'], url_path='chama-members')
    def chama_members_report(self, request):
        total_chamas = Chama.objects.count()
        total_members = ChamaMembership.objects.count()
        active_chamas = Chama.objects.filter(status='active').count()

        total_pool = Chama.objects.aggregate(total=Sum('total_pool_balance'))['total'] or Decimal('0.00')

        chamas_data = Chama.objects.select_related('admin').order_by('-created_at')[:10]
        chamas_list = []

        for chama in chamas_data:
            memberships = ChamaMembership.objects.select_related('user').filter(chama=chama)
            members = [
                {
                    'user_id': m.user.id,
                    'username': m.user.username,
                    'email': m.user.email,
                    'full_name': m.user.full_name,
                    'phone_number': m.user.phone_number,
                    'role': m.role,
                    'joined_at': m.joined_at.isoformat(),
                }
                for m in memberships
            ]
            chamas_list.append({
                'id': chama.id,
                'name': chama.name,
                'description': chama.description,
                'admin': chama.admin.username,
                'admin_email': chama.admin.email,
                'member_count': chama.member_count,
                'target_amount': str(chama.target_amount),
                'monthly_contribution': str(chama.monthly_contribution),
                'contribution_frequency': chama.contribution_frequency,
                'total_pool_balance': str(chama.total_pool_balance),
                'status': chama.status,
                'invite_code': chama.invite_code,
                'created_at': chama.created_at.isoformat(),
                'members': members,
            })

        return Response({
            'summary': {
                'total_chamas': total_chamas,
                'total_members': total_members,
                'active_chamas': active_chamas,
                'total_pool_balance': str(total_pool),
            },
            'chamas': chamas_list,
        })


# --- Cheque services --------------------------------------------------------

CHEQUE_LEAVES_CHOICES = (25, 50, 100)


class ChequeBookRequestViewSet(viewsets.ModelViewSet):
    """User cheque book requests. POST deducts the service fee atomically."""
    serializer_class = ChequeBookRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChequeBookRequest.objects.filter(
            user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        leaves = request.data.get('leaves')
        delivery_method = request.data.get('delivery_method', 'branch')
        delivery_address = (request.data.get('delivery_address') or '').strip()

        try:
            leaves = int(leaves)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid number of leaves'},
                            status=status.HTTP_400_BAD_REQUEST)
        if leaves not in CHEQUE_LEAVES_CHOICES:
            return Response(
                {'error': f'Leaves must be one of {list(CHEQUE_LEAVES_CHOICES)}'},
                status=status.HTTP_400_BAD_REQUEST)
        if delivery_method not in (ChequeBookRequest.DeliveryMethod.BRANCH,
                                   ChequeBookRequest.DeliveryMethod.COURIER):
            return Response({'error': 'Invalid delivery method'},
                            status=status.HTTP_400_BAD_REQUEST)
        if delivery_method == ChequeBookRequest.DeliveryMethod.COURIER and not delivery_address:
            return Response({'error': 'Delivery address is required for courier delivery'},
                            status=status.HTTP_400_BAD_REQUEST)

        fee = models_decimal(CHEQUE_COURIER_FEE if delivery_method == 'courier'
                             else CHEQUE_BOOK_FEE)

        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=request.user.pk)
            if locked_user.balance < fee:
                return Response(
                    {'error': f'Insufficient balance. KSh {fee} cheque book fee applies.'},
                    status=status.HTTP_400_BAD_REQUEST)

            User.objects.filter(pk=locked_user.pk).update(balance=F('balance') - fee)
            order = ChequeBookRequest.objects.create(
                user=locked_user,
                leaves=leaves,
                delivery_method=delivery_method,
                delivery_address=delivery_address,
                fee=fee,
            )
            Transaction.objects.create(
                user=locked_user,
                amount=fee,
                category='cheque_book',
                type='withdrawal',
                description=f'Cheque book fee ({leaves} leaves, '
                            f'{order.get_delivery_method_display()}) • {order.reference}',
                date=timezone.now(),
            )

        locked_user.refresh_from_db(fields=['balance'])
        data = self.get_serializer(order).data
        data['balance'] = str(locked_user.balance)
        return Response(data, status=status.HTTP_201_CREATED)


class StopPaymentOrderViewSet(viewsets.ModelViewSet):
    """Stop-payment orders. POST deducts the flat fee atomically."""
    serializer_class = StopPaymentOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StopPaymentOrder.objects.filter(
            user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        cheque_from = (request.data.get('cheque_from') or '').strip()
        cheque_to = (request.data.get('cheque_to') or '').strip()
        reason = request.data.get('reason', 'lost')
        date_issued = request.data.get('date_issued')

        if not cheque_from.isdigit() or len(cheque_from) > 20:
            return Response({'error': 'A valid starting cheque number is required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if cheque_to and not cheque_to.isdigit():
            return Response({'error': 'Invalid ending cheque number'},
                            status=status.HTTP_400_BAD_REQUEST)
        if reason not in StopPaymentOrder.Reason.values:
            return Response({'error': 'Invalid reason'},
                            status=status.HTTP_400_BAD_REQUEST)

        parsed_date = None
        if date_issued:
            try:
                parsed_date = datetime.strptime(str(date_issued)[:10], '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Date issued must be YYYY-MM-DD'},
                                status=status.HTTP_400_BAD_REQUEST)

        fee = models_decimal(STOP_PAYMENT_FEE)

        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=request.user.pk)
            if locked_user.balance < fee:
                return Response(
                    {'error': f'Insufficient balance. KSh {STOP_PAYMENT_FEE} '
                              'stop-payment fee applies.'},
                    status=status.HTTP_400_BAD_REQUEST)

            User.objects.filter(pk=locked_user.pk).update(balance=F('balance') - fee)
            order = StopPaymentOrder.objects.create(
                user=locked_user,
                cheque_from=cheque_from,
                cheque_to=cheque_to or '',
                reason=reason,
                date_issued=parsed_date,
                fee=fee,
            )
            Transaction.objects.create(
                user=locked_user,
                amount=fee,
                category='stop_payment',
                type='withdrawal',
                description=f'Stop payment on cheque {cheque_from}'
                            f'{"–" + cheque_to if cheque_to else ""} • {order.reference}',
                date=timezone.now(),
            )

        locked_user.refresh_from_db(fields=['balance'])
        data = self.get_serializer(order).data
        data['balance'] = str(locked_user.balance)
        return Response(data, status=status.HTTP_201_CREATED)


# --- Foreign exchange -------------------------------------------------------

class FxViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='rates')
    def rates(self, request):
        qs = FxRate.objects.filter(is_active=True).order_by('code')
        return Response(FxRateSerializer(qs, many=True).data)

    @staticmethod
    def _get_wallet(user, code):
        wallet, _created = CurrencyWallet.objects.get_or_create(user=user, code=code)
        return wallet

    @action(detail=False, methods=['post'], url_path='exchange')
    def exchange(self, request):
        from_code = str(request.data.get('from', '')).upper().strip()
        to_code = str(request.data.get('to', '')).upper().strip()
        raw_amount = request.data.get('amount')

        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Invalid amount'},
                            status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Amount must be greater than zero'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Exactly one side of the pair must be KES.
        if from_code == to_code:
            return Response({'error': 'Choose two different currencies'},
                            status=status.HTTP_400_BAD_REQUEST)
        if from_code == 'KES':
            foreign_code = to_code
            selling_kes = True
        elif to_code == 'KES':
            foreign_code = from_code
            selling_kes = False
        else:
            return Response({'error': 'One side of the pair must be KES'},
                            status=status.HTTP_400_BAD_REQUEST)

        rate_obj = FxRate.objects.filter(code=foreign_code, is_active=True).first()
        if rate_obj is None:
            return Response({'error': f'{foreign_code} exchanges are not available'},
                            status=status.HTTP_400_BAD_REQUEST)

        rate = rate_obj.rate
        fee = models_decimal(FX_FEE)
        reference = 'FX' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=request.user.pk)
            foreign_wallet = self._get_wallet(locked_user, foreign_code)

            if selling_kes:
                total_debit = models_decimal(amount + fee)
                if locked_user.balance < total_debit:
                    return Response(
                        {'error': f'Insufficient balance. KSh {total_debit} would be '
                                  'debited (amount + fee).'},
                        status=status.HTTP_400_BAD_REQUEST)
                foreign_credit = (amount / rate).quantize(Decimal('0.0001'))
                kes_credit = Decimal('0')

                User.objects.filter(pk=locked_user.pk).update(
                    balance=F('balance') - total_debit)
                CurrencyWallet.objects.filter(pk=foreign_wallet.pk).update(
                    balance=F('balance') + foreign_credit)
            else:
                if foreign_wallet.balance < amount:
                    return Response(
                        {'error': f'Insufficient {foreign_code} balance. '
                                  f'Available: {models_decimal(foreign_wallet.balance)}'},
                        status=status.HTTP_400_BAD_REQUEST)
                gross_kes = models_decimal(amount * rate)
                kes_credit = gross_kes - fee
                if kes_credit <= 0:
                    return Response({'error': 'Exchange value is lower than the fee'},
                                    status=status.HTTP_400_BAD_REQUEST)
                foreign_credit = Decimal('0')
                total_debit = amount

                CurrencyWallet.objects.filter(pk=foreign_wallet.pk).update(
                    balance=F('balance') - amount)
                User.objects.filter(pk=locked_user.pk).update(
                    balance=F('balance') + kes_credit)

            if selling_kes:
                Transaction.objects.create(
                    user=locked_user,
                    amount=models_decimal(total_debit),
                    broker_fee=fee,
                    government_tax=Decimal('0'),
                    category='fx_exchange',
                    type='withdrawal',
                    description=(
                        f'Bought {models_decimal(foreign_credit)} {foreign_code} '
                        f'at 1 {foreign_code} = {rate} KES • {reference}'
                    ),
                    date=timezone.now(),
                )
            else:
                Transaction.objects.create(
                    user=locked_user,
                    amount=models_decimal(kes_credit),
                    category='fx_exchange',
                    type='deposit',
                    description=(
                        f'Sold {models_decimal(amount)} {foreign_code} '
                        f'at 1 {foreign_code} = {rate} KES • {reference}'
                    ),
                    date=timezone.now(),
                )

        locked_user.refresh_from_db(fields=['balance'])
        foreign_wallet.refresh_from_db(fields=['balance'])

        sent_amount = models_decimal(amount if selling_kes else amount)
        got_amount = models_decimal(foreign_credit if selling_kes else kes_credit)
        return Response({
            'status': 'success',
            'reference': reference,
            'sent_currency': 'KES' if selling_kes else foreign_code,
            'sent_amount': str(sent_amount),
            'got_currency': foreign_code if selling_kes else 'KES',
            'got_amount': str(got_amount),
            'rate': f'1 {foreign_code} = {rate} KES',
            'fee': str(models_decimal(fee)),
            'kes_balance': str(models_decimal(locked_user.balance)),
            'foreign_balance': str(models_decimal(foreign_wallet.balance)),
        }, status=status.HTTP_201_CREATED)


# --- Crypto trading ---------------------------------------------------------

class CryptoViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='portfolio')
    def portfolio(self, request):
        assets = CryptoAsset.objects.filter(is_active=True).order_by('id')
        holdings = {
            h.asset.symbol: h.quantity
            for h in CryptoHolding.objects.filter(user=request.user, asset__in=assets)
            .select_related('asset')
        }
        rows = []
        portfolio_total = Decimal('0')
        for asset in assets:
            qty = holdings.get(asset.symbol, Decimal('0'))
            value = (qty * asset.price_kes).quantize(Decimal('0.01'))
            portfolio_total += value
            rows.append({
                **CryptoAssetSerializer(asset).data,
                'quantity': str(qty),
                'value_kes': str(value),
            })
        return Response({
            'assets': rows,
            'portfolio_total': str(models_decimal(portfolio_total)),
            'available_balance': str(request.user.balance),
        })

    @action(detail=False, methods=['post'], url_path='trade')
    def trade(self, request):
        symbol = str(request.data.get('symbol', '')).upper().strip()
        trade_action = str(request.data.get('action', '')).lower().strip()
        raw_amount = request.data.get('amount')

        if trade_action not in ('buy', 'sell'):
            return Response({'error': 'Action must be buy or sell'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Invalid amount'},
                            status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Amount must be greater than zero'},
                            status=status.HTTP_400_BAD_REQUEST)

        asset = CryptoAsset.objects.filter(symbol=symbol, is_active=True).first()
        if asset is None:
            return Response({'error': f'{symbol} trading is not available'},
                            status=status.HTTP_400_BAD_REQUEST)

        price = asset.price_kes
        quantity = (amount / price).quantize(Decimal('0.00000001'))
        fee = models_decimal(amount * CRYPTO_TRADE_FEE_RATE)
        reference = 'CR' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        with transaction.atomic():
            holding, _created = CryptoHolding.objects.select_for_update().get_or_create(
                user=request.user, asset=asset)

            if trade_action == 'buy':
                total_debit = models_decimal(amount + fee)
                if request.user.balance < total_debit:
                    return Response(
                        {'error': f'Insufficient balance. Available: '
                                  f'{request.user.balance} KSh'},
                        status=status.HTTP_400_BAD_REQUEST)
                User.objects.filter(pk=request.user.pk).update(
                    balance=F('balance') - total_debit)
                CryptoHolding.objects.filter(pk=holding.pk).update(
                    quantity=F('quantity') + quantity)
                credit_note = ''
            else:
                if holding.quantity < quantity:
                    return Response(
                        {'error': f'You only hold '
                                  f'{holding.quantity.normalize()} {symbol}'},
                        status=status.HTTP_400_BAD_REQUEST)
                net_credit = models_decimal(amount - fee)
                User.objects.filter(pk=request.user.pk).update(
                    balance=F('balance') + net_credit)
                CryptoHolding.objects.filter(pk=holding.pk).update(
                    quantity=F('quantity') - quantity)
                credit_note = f' · credited KSh {net_credit}'

            Transaction.objects.create(
                user=request.user,
                amount=models_decimal(total_debit if trade_action == 'buy'
                                      else amount),
                broker_fee=fee,
                government_tax=Decimal('0'),
                category='crypto_trade',
                type='withdrawal' if trade_action == 'buy' else 'deposit',
                description=(
                    f'{trade_action.title()} {quantity.normalize()} {symbol} '
                    f'@ KSh {price}/coin • {reference}{credit_note}'
                ),
                date=timezone.now(),
            )

        request.user.refresh_from_db(fields=['balance'])
        holding.refresh_from_db(fields=['quantity'])
        new_value = (holding.quantity * price).quantize(Decimal('0.01'))

        return Response({
            'status': 'success',
            'reference': reference,
            'action': trade_action,
            'symbol': symbol,
            'name': asset.name,
            'quantity': str(holding.quantity),
            'value_kes': str(new_value),
            'fee': str(models_decimal(fee)),
            'available_balance': str(models_decimal(request.user.balance)),
        }, status=status.HTTP_201_CREATED)


# --- Digital cheques --------------------------------------------------------

class ChequeViewSet(viewsets.ViewSet):
    """Digital cheque lifecycle: issue, deposit/clear, cancel."""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='issued')
    def issued(self, request):
        qs = Cheque.objects.filter(issuer=request.user).select_related('payee') \
            .order_by('-issued_at')
        return Response(ChequeSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='received')
    def received(self, request):
        qs = Cheque.objects.filter(payee=request.user).select_related('issuer') \
            .order_by('-issued_at')
        return Response(ChequeSerializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='issue')
    def issue(self, request):
        payee_key = str(request.data.get('payee', '')).strip()
        memo = str(request.data.get('memo', '')).strip()[:140]
        raw_amount = request.data.get('amount')
        raw_due = request.data.get('due_date')

        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Invalid amount'},
                            status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Amount must be greater than zero'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not payee_key:
            return Response({'error': 'Payee is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        from django.db.models import Q as _Q
        payee = User.objects.filter(
            _Q(username__iexact=payee_key) | _Q(email__iexact=payee_key)).first()
        if payee is None:
            return Response({'error': f'No registered user found for "{payee_key}"'},
                            status=status.HTTP_400_BAD_REQUEST)
        if payee.pk == request.user.pk:
            return Response({'error': 'You cannot issue a cheque to yourself'},
                            status=status.HTTP_400_BAD_REQUEST)

        due_date = None
        if raw_due:
            try:
                due_date = datetime.strptime(str(raw_due)[:10], '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Due date must be YYYY-MM-DD'},
                                status=status.HTTP_400_BAD_REQUEST)

        cheque = Cheque.objects.create(
            issuer=request.user,
            payee=payee,
            amount=models_decimal(amount),
            memo=memo,
            due_date=due_date,
        )
        data = ChequeSerializer(cheque).data
        data['funds_available'] = request.user.balance >= models_decimal(amount)
        if not data['funds_available']:
            data['warning'] = ('Your balance is lower than the cheque amount; '
                               'the cheque will bounce unless you top up before '
                               'it is deposited.')
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='clear')
    def clear(self, request):
        number = str(request.data.get('cheque_number', '')).strip()
        if not number:
            return Response({'error': 'Cheque number is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        candidates = {number}
        if number.isdigit():
            candidates.add(number.zfill(6))
        cheque = (Cheque.objects.select_related('issuer', 'payee')
                  .filter(cheque_number__in=candidates).first())
        if cheque is None:
            return Response({'error': 'No cheque found with that number'},
                            status=status.HTTP_404_NOT_FOUND)
        if cheque.payee_id != request.user.pk:
            return Response(
                {'error': 'This cheque was not issued in your favour'},
                status=status.HTTP_403_FORBIDDEN)
        if cheque.status != Cheque.Status.PENDING:
            return Response(
                {'error': f'Cheque is {cheque.status}'
                          + (f' ({cheque.status_note})' if cheque.status_note else '')},
                status=status.HTTP_400_BAD_REQUEST)
        if cheque.due_date and timezone.now().date() < cheque.due_date:
            return Response(
                {'error': f'This cheque is post-dated; it can be deposited '
                          f'from {cheque.due_date.isoformat()} onwards'},
                status=status.HTTP_400_BAD_REQUEST)

        amount = models_decimal(cheque.amount)

        if cheque.is_stop_payment_active():
            cheque.status = Cheque.Status.STOPPED
            cheque.status_note = 'Stop payment order active on this cheque'
            cheque.save(update_fields=['status', 'status_note', 'updated_at'])
            return Response(
                {'error': 'Deposit rejected: the issuer placed a stop-payment '
                          'order on this cheque'},
                status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            locked_payer = User.objects.select_for_update().get(pk=cheque.issuer_id)
            locked_payee = User.objects.select_for_update().get(pk=request.user.pk)

            if locked_payer.balance < amount:
                cheque.status = Cheque.Status.BOUNCED
                cheque.status_note = f'Insufficient funds at deposit ({timezone.now().date().isoformat()})'
                cheque.save(update_fields=['status', 'status_note', 'updated_at'])
                return Response(
                    {'error': f'Cheque bounced: issuer has insufficient funds '
                              f'(KSh {locked_payer.balance})'},
                    status=status.HTTP_400_BAD_REQUEST)

            User.objects.filter(pk=locked_payer.pk).update(
                balance=F('balance') - amount)
            User.objects.filter(pk=locked_payee.pk).update(
                balance=F('balance') + amount)

            Transaction.objects.create(
                user=locked_payer,
                amount=amount,
                category='cheque_clearance',
                type='withdrawal',
                description=f'Cheque {cheque.cheque_number} cashed by '
                            f'{locked_payee.username} • {cheque.reference}',
                date=timezone.now(),
            )
            Transaction.objects.create(
                user=locked_payee,
                amount=amount,
                category='cheque_clearance',
                type='deposit',
                description=f'Cheque {cheque.cheque_number} from '
                            f'{locked_payer.username} • {cheque.reference}',
                date=timezone.now(),
            )

            cheque.status = Cheque.Status.CLEARED
            cheque.cleared_at = timezone.now()
            cheque.save(update_fields=['status', 'cleared_at', 'updated_at'])

        locked_payer.refresh_from_db(fields=['balance'])
        locked_payee.refresh_from_db(fields=['balance'])

        return Response({
            'status': 'success',
            'cheque_number': cheque.cheque_number,
            'reference': cheque.reference,
            'from_user': locked_payer.username,
            'amount': str(amount),
            'kes_balance': str(models_decimal(locked_payee.balance)),
            'cleared_at': cheque.cleared_at.isoformat(),
        })

    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request):
        number = str(request.data.get('cheque_number', '')).strip()
        cheque = Cheque.objects.filter(cheque_number=number).first()
        if cheque is None:
            return Response({'error': 'No cheque found with that number'},
                            status=status.HTTP_404_NOT_FOUND)
        if cheque.issuer_id != request.user.pk:
            return Response({'error': 'Only the issuer can cancel a cheque'},
                            status=status.HTTP_403_FORBIDDEN)
        if cheque.status != Cheque.Status.PENDING:
            return Response(
                {'error': f'Only pending cheques can be cancelled '
                          f'(current status: {cheque.status})'},
                status=status.HTTP_400_BAD_REQUEST)

        cheque.status = Cheque.Status.CANCELLED
        cheque.status_note = 'Cancelled by issuer'
        cheque.save(update_fields=['status', 'status_note', 'updated_at'])
        return Response(ChequeSerializer(cheque).data)
