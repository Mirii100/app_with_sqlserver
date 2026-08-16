from rest_framework import serializers
from .models import MpesaPayment


class MpesaPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MpesaPayment
        fields = '__all__'
        read_only_fields = [
            'reference',
            'merchant_request_id',
            'checkout_request_id',
            'status',
            'result_code',
            'result_desc',
            'mpesa_receipt_number',
            'completed_at',
        ]


class STKPushRequestSerializer(serializers.Serializer):
    """Input payload for initiating an M-Pesa STK Push."""

    ITEM_TYPE_CHOICES = [
        ('buy_goods', 'Buy Goods / Till'),
        ('buy_goods_services', 'Buy Goods and Services'),
        ('paybill', 'Paybill'),
    ]

    phone_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    item_type = serializers.ChoiceField(choices=ITEM_TYPE_CHOICES)
    item_id = serializers.CharField(max_length=20)
    account_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    transaction_desc = serializers.CharField(max_length=255, required=False, allow_blank=True)
