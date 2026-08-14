from rest_framework import serializers
import json

from .models import BillerCategory, SavingsGoal, Transaction, GoalTransaction, UserLoanLimit, Budget

class BillerCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BillerCategory
        fields = '__all__'

class SavingsGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsGoal
        fields = '__all__'
        read_only_fields = ['user']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['reference', 'broker_fee', 'government_tax']

class GoalTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalTransaction
        fields = '__all__'
        read_only_fields = ['reference']

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ('categories', 'budget_limits'):
            value = data.get(field)
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    data[field] = parsed if isinstance(parsed, dict) else {}
                except (TypeError, ValueError):
                    data[field] = {}
        return data

class UserLoanLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLoanLimit
        fields = '__all__'
