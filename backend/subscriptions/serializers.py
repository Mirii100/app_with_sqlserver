from rest_framework import serializers

from .models import Subscription, SubscriptionWallet, UserSubscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            'id',
            'name',
            'description',
            'price',
            'billing_cycle',
            'active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='subscription.name', read_only=True)
    description = serializers.CharField(source='subscription.description', read_only=True)
    price = serializers.DecimalField(source='subscription.price', max_digits=15, decimal_places=2, read_only=True)
    billing_cycle = serializers.CharField(source='subscription.billing_cycle', read_only=True)
    subscription_id = serializers.IntegerField(source='subscription.id', read_only=True)

    class Meta:
        model = UserSubscription
        fields = [
            'id',
            'user',
            'subscription',
            'subscription_id',
            'name',
            'description',
            'price',
            'billing_cycle',
            'status',
            'subscribed_at',
        ]
        read_only_fields = ['id', 'subscribed_at']


class SubscriptionWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionWallet
        fields = [
            'id',
            'user',
            'account_number',
            'balance',
            'currency',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'account_number', 'balance', 'currency', 'created_at', 'updated_at']
