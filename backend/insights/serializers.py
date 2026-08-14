from rest_framework import serializers

from .models import FinancialAdvice


class FinancialAdviceSerializer(serializers.ModelSerializer):
    advice_type_display = serializers.CharField(source='get_advice_type_display', read_only=True)

    class Meta:
        model = FinancialAdvice
        fields = [
            'id',
            'title',
            'message',
            'advice_type',
            'advice_type_display',
            'is_read',
            'created_at',
        ]
