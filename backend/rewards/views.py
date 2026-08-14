from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Reward, RewardTransaction
from .serializers import RewardSerializer, RewardTransactionSerializer


class RewardViewSet(viewsets.ReadOnlyModelViewSet):
    """Rewards catalogue plus point balance and redemption."""

    serializer_class = RewardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Reward.objects.filter(is_active=True)

    @action(detail=False, methods=['get'], url_path='points')
    def points(self, request):
        return Response({'points': request.user.points})

    @action(detail=False, methods=['get'], url_path='my-transactions')
    def my_transactions(self, request):
        qs = RewardTransaction.objects.filter(user=request.user).select_related('reward')
        return Response(RewardTransactionSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='redeem')
    def redeem(self, request, pk=None):
        reward = self.get_object()
        user = request.user

        if user.points < reward.points_cost:
            return Response(
                {'error': f'You need {reward.points_cost} points to redeem {reward.name}. '
                          f'You have {user.points} points.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.points -= reward.points_cost
            user.save(update_fields=['points'])
            tx = RewardTransaction.objects.create(
                user=user,
                reward=reward,
                points_cost=reward.points_cost,
            )

        return Response({
            'status': 'success',
            'transaction': RewardTransactionSerializer(tx).data,
            'points_remaining': user.points,
        }, status=status.HTTP_201_CREATED)
