from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Chama, ChamaMembership
from .serializers import ChamaSerializer, ChamaMembershipSerializer
from transactions.models import Transaction

User = get_user_model()


class ChamaViewSet(viewsets.ModelViewSet):
    queryset = Chama.objects.all()
    serializer_class = ChamaSerializer

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

        membership, created = ChamaMembership.objects.get_or_create(chama=chama, user_id=user_id)

        if created:
            chama.member_count += 1
            chama.save()
            return Response({'status': 'Joined chama'}, status=status.HTTP_201_CREATED)
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

        if user.balance < amount_value:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            User.objects.filter(id=user.id).update(balance=F('balance') - amount_value)

            Transaction.objects.create(
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

        user.refresh_from_db()
        chama.refresh_from_db()

        return Response({
            'status': 'success',
            'amount': str(amount_value),
            'chama_name': chama.name,
            'new_pool_balance': str(chama.total_pool_balance),
            'user_balance': str(user.balance),
        }, status=status.HTTP_201_CREATED)


class ChamaMembershipViewSet(viewsets.ModelViewSet):
    queryset = ChamaMembership.objects.all()
    serializer_class = ChamaMembershipSerializer
