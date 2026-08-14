from decimal import Decimal

from rest_framework import serializers

from .models import Stock


class StockSerializer(serializers.ModelSerializer):
    change_percent = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            'id',
            'code',
            'name',
            'sector',
            'current_price',
            'previous_close',
            'change_percent',
            'is_active',
        ]

    def get_change_percent(self, obj):
        return obj.change_percent.quantize(Decimal('0.01'))
