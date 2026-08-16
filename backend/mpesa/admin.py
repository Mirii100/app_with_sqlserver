from django.contrib import admin
from .models import MpesaPayment


@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'user',
        'phone_number',
        'amount',
        'item_type',
        'item_id',
        'status',
        'result_code',
        'mpesa_receipt_number',
        'created_at',
        'completed_at',
    )
    list_filter = (
        'status',
        'item_type',
        'created_at',
    )
    search_fields = (
        'reference',
        'checkout_request_id',
        'merchant_request_id',
        'phone_number',
        'mpesa_receipt_number',
        'user__username',
        'user__email',
    )
    readonly_fields = (
        'reference',
        'merchant_request_id',
        'checkout_request_id',
        'user',
        'item_type',
        'item_id',
        'account_reference',
        'phone_number',
        'amount',
        'transaction_desc',
        'result_code',
        'result_desc',
        'mpesa_receipt_number',
        'ledger_transaction',
        'created_at',
        'updated_at',
        'completed_at',
    )
    list_select_related = ('user',)
    list_per_page = 30
