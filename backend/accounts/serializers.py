from rest_framework import serializers
from .models import Account, Biller


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    available_balance = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ['balance', 'available_balance']

    def get_balance(self, obj):
        """Always reflect the User's balance — single source of truth."""
        return obj.user.balance

    def get_available_balance(self, obj):
        """Always reflect the User's balance — single source of truth."""
        return obj.user.balance


class BillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biller
        fields = '__all__'
