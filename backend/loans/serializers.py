from rest_framework import serializers

from .models import Loan, LoanProduct


class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = [
            'id',
            'user',
            'name',
            'description',
            'is_best_match',
            'is_outline',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            'id',
            'user',
            'loan_product',
            'amount',
            'approved_amount',
            'outstanding_amount',
            'interest_rate',
            'duration_months',
            'status',
            'purpose',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]