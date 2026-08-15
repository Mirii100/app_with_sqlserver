from decimal import Decimal
import json
from datetime import timedelta
from django.db import transaction
from django.db.models import F, Sum, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from accounts.models import Account, Biller
from accounts.models import generate_biller_account_number
from chamas.models import Chama, ChamaMembership
from loans.models import Loan
from stocks.fees import compute_tiered_charges, record_charges, _money
from .models import BillerCategory, Transaction, SavingsGoal, GoalTransaction, Budget, UserLoanLimit
from .serializers import BillerCategorySerializer, TransactionSerializer, SavingsGoalSerializer, GoalTransactionSerializer, BudgetSerializer, UserLoanLimitSerializer

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
