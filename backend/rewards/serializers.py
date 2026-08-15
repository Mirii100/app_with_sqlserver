from rest_framework import serializers

from .models import Reward, RewardTransaction, PointsAward


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ['id', 'name', 'description', 'points_cost', 'icon', 'is_active']


class RewardTransactionSerializer(serializers.ModelSerializer):
    reward_name = serializers.CharField(source='reward.name', read_only=True)
    reward_icon = serializers.CharField(source='reward.icon', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RewardTransaction
        fields = [
            'id',
            'reward',
            'reward_name',
            'reward_icon',
            'points_cost',
            'status',
            'status_display',
            'created_at',
        ]


class PointsAwardSerializer(serializers.ModelSerializer):
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)

    class Meta:
        model = PointsAward
        fields = [
            'id',
            'reason',
            'reason_display',
            'points',
            'description',
            'created_at',
        ]
