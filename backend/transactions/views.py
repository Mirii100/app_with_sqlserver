from decimal import Decimal
from django.db import transaction
from django.db.models import F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from accounts.models import Account
from .models import Transaction, SavingsGoal, GoalTransaction, Budget, UserLoanLimit
from .serializers import TransactionSerializer, SavingsGoalSerializer, GoalTransactionSerializer, BudgetSerializer, UserLoanLimitSerializer
from django.utils import timezone

User = get_user_model()


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

            # Transaction.objects.create(
            #     user=sender,
            #     amount=amount_value,
            #     category='transfer_out',
            #     type='withdrawal',
            #     description=f"Transfer to {recipient.phone_number}",
            # )
            # Transaction.objects.create(
            #     user=recipient,
            #     amount=amount_value,
            #     category='transfer_in',
            #     type='deposit',
            #     description=f"Transfer from {sender.phone_number}",
            # )
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

class GoalTransactionViewSet(viewsets.ModelViewSet):
    queryset = GoalTransaction.objects.all()
    serializer_class = GoalTransactionSerializer

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer

class UserLoanLimitViewSet(viewsets.ModelViewSet):
    queryset = UserLoanLimit.objects.all()
    serializer_class = UserLoanLimitSerializer
