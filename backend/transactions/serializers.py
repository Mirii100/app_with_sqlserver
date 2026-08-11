from rest_framework import serializers
from .models import Transaction, SavingsGoal, GoalTransaction, Budget, UserLoanLimit

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

class SavingsGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsGoal
        fields = '__all__'

class GoalTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalTransaction
        fields = '__all__'

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = '__all__'

class UserLoanLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLoanLimit
        fields = '__all__'
