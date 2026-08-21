from rest_framework import serializers
import json

from .models import (BillerCategory, SavingsGoal, Transaction, GoalTransaction,
                     UserLoanLimit, Budget, ChequeBookRequest, StopPaymentOrder,
                     FxRate, CurrencyWallet, CryptoAsset, CryptoHolding, Cheque)

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


class ChequeBookRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChequeBookRequest
        fields = ['id', 'leaves', 'delivery_method', 'delivery_address',
                  'fee', 'status', 'reference', 'created_at']
        read_only_fields = ['fee', 'status', 'reference', 'created_at']


class StopPaymentOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StopPaymentOrder
        fields = ['id', 'cheque_from', 'cheque_to', 'reason', 'date_issued',
                  'fee', 'status', 'reference', 'created_at']
        read_only_fields = ['fee', 'status', 'reference', 'created_at']


class FxRateSerializer(serializers.ModelSerializer):
    direction = serializers.CharField(read_only=True)

    class Meta:
        model = FxRate
        fields = ['code', 'rate', 'previous_rate', 'direction', 'updated_at']


class CryptoAssetSerializer(serializers.ModelSerializer):
    change_pct = serializers.CharField(read_only=True)

    class Meta:
        model = CryptoAsset
        fields = ['id', 'symbol', 'name', 'glyph', 'color_hex',
                  'price_kes', 'change_pct']



class ChequeSerializer(serializers.ModelSerializer):
    issuer_username = serializers.CharField(source='issuer.username', read_only=True)
    payee_username = serializers.CharField(source='payee.username', read_only=True)

    class Meta:
        model = Cheque
        fields = ['id', 'cheque_number', 'amount', 'memo', 'due_date', 'status',
                  'status_note', 'reference', 'issued_at', 'cleared_at',
                  'issuer', 'issuer_username', 'payee', 'payee_username']
        read_only_fields = ['cheque_number', 'status', 'status_note',
                            'reference', 'issued_at', 'cleared_at']
