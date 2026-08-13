from decimal import Decimal
from django.db import transaction
from django.db.models import F, Sum, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from accounts.models import Account
from chamas.models import Chama, ChamaMembership
from loans.models import Loan
from .models import BillerCategory, Transaction, SavingsGoal, GoalTransaction, Budget, UserLoanLimit
from .serializers import BillerCategorySerializer, TransactionSerializer, SavingsGoalSerializer, GoalTransactionSerializer, BudgetSerializer, UserLoanLimitSerializer

User = get_user_model()

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
            account = Account.objects.get(user_id=user_id)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        if account.balance < amount_value:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            account.balance -= amount_value
            account.save()

            Transaction.objects.create(
                user=account.user,
                amount=amount_value,
                category=category,
                type='withdrawal',
                description=description or f"Payment to {biller_id}",
                date=timezone.now(),
            )

        return Response({'status': 'success'}, status=status.HTTP_201_CREATED)

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

        reference = request.data.get('reference', '')
        description = request.data.get('description', 'Deposit')

        with transaction.atomic():
            Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='deposit',
                type='deposit',
                description=description,
                date=timezone.now(),
            )

            User.objects.filter(id=user.id).update(balance=F('balance') + amount_value)

        user.refresh_from_db()

        return Response({
            'status': 'success',
            'reference': reference,
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

        if user.balance < amount_value:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        reference = request.data.get('reference', '')
        description = request.data.get('description', 'Withdrawal')

        with transaction.atomic():
            Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='withdrawal',
                type='withdrawal',
                description=description,
                date=timezone.now(),
            )

            User.objects.filter(id=user.id).update(balance=F('balance') - amount_value)

        user.refresh_from_db()

        return Response({
            'status': 'success',
            'reference': reference,
            'new_balance': str(user.balance),
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

        if sender.balance < amount_value:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            User.objects.filter(id=sender.id).update(balance=F('balance') - amount_value)
            User.objects.filter(id=recipient.id).update(balance=F('balance') + amount_value)

            Transaction.objects.create(
                    user=sender,
                    amount=amount_value,
                    category='transfer_out',
                    type='withdrawal',
                    description=f"Transfer to {recipient.phone_number}",
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

        sender.refresh_from_db()
        recipient.refresh_from_db()

        return Response({'status': 'success', 'reference': request.data.get('reference', '')}, status=status.HTTP_201_CREATED)

class SavingsGoalViewSet(viewsets.ModelViewSet):
    queryset = SavingsGoal.objects.all()
    serializer_class = SavingsGoalSerializer

    @action(detail=True, methods=['post'], url_path='fund')
    def fund(self, request, pk=None):
        goal = self.get_object()
        user_id = request.data.get('user')
        amount = request.data.get('amount')

        if not all([user_id, amount]):
            return Response({'error': 'user and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        amount_value = Decimal(str(amount))

        if user.balance < amount_value:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            User.objects.filter(id=user.id).update(balance=F('balance') - amount_value)

            Transaction.objects.create(
                user=user,
                amount=amount_value,
                category='savings_goal_funding',
                type='withdrawal',
                description=f'Funding goal: {goal.title}',
                date=timezone.now(),
            )

            SavingsGoal.objects.filter(id=goal.id).update(
                saved_amount=F('saved_amount') + amount_value
            )

        user.refresh_from_db()
        goal.refresh_from_db()

        return Response({
            'status': 'success',
            'amount': str(amount_value),
            'goal_title': goal.title,
            'new_saved_amount': str(goal.saved_amount),
            'user_balance': str(user.balance),
        }, status=status.HTTP_201_CREATED)


class GoalTransactionViewSet(viewsets.ModelViewSet):
    queryset = GoalTransaction.objects.all()
    serializer_class = GoalTransactionSerializer

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer

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
