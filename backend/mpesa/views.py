"""API views for M-Pesa STK Push integration.

Exposes two endpoints (both under ``/api/mpesa/``):

* ``POST /api/mpesa/stk-push/`` – initiate an STK Push (auth required)
* ``POST /api/mpesa/callback/``  – receive Safaricom callback (public)
"""

import json
import string
import random
import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction, models
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from core.models import User
from transactions.models import Transaction
from stocks.fees import compute_tiered_charges, record_charges, _money
from .models import MpesaPayment
from .serializers import MpesaPaymentSerializer, STKPushRequestSerializer
from .daraja import send_stk_push, query_stk_status, DarajaAPIError

logger = logging.getLogger(__name__)


def _generate_reference():
    """Generate a unique reference for STK Push requests."""
    chars = string.ascii_uppercase + string.digits
    while True:
        ref = 'ALE' + ''.join(random.choices(chars, k=9))
        if not MpesaPayment.objects.filter(reference=ref).exists():
            return ref


def _normalise_phone(phone_number):
    """Return phone in 254XXXXXXXXX format."""
    phone = phone_number.strip().replace(' ', '').replace('+', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    return phone


@method_decorator(csrf_exempt, name='dispatch')
class STKPushViewSet(viewsets.ViewSet):
    """Authenticated endpoint for initiating M-Pesa STK Push requests."""

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='stk-push')
    def stk_push(self, request):
        serializer = STKPushRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        phone_number = _normalise_phone(data['phone_number'])
        amount = data['amount']
        item_type = data['item_type']
        item_id = data['item_id']

        user = request.user

        with transaction.atomic():
            payment = MpesaPayment.objects.create(
                user=user,
                reference=_generate_reference(),
                item_type=item_type,
                item_id=item_id,
                account_reference=data.get('account_reference', ''),
                phone_number=phone_number,
                amount=amount,
                transaction_desc=data.get('transaction_desc', 'Alexia wallet top-up'),
                status=MpesaPayment.Status.PENDING,
            )

            try:
                daraja_response = send_stk_push(
                    phone_number=phone_number,
                    amount=int(amount),
                    item_type=item_type,
                    item_id=item_id,
                    account_reference=data.get('account_reference'),
                    transaction_desc=data.get('transaction_desc', 'Alexia wallet top-up'),
                )
            except DarajaAPIError as exc:
                logger.error(
                    'STK Push failed: %s | raw_response: %s',
                    exc, exc.raw_response,
                )
                payment.mark_failed(
                    code=getattr(exc, 'status_code', 'N/A'),
                    desc=str(exc),
                )
                logger.error('STK Push failed for user %s: %s', user, exc)
                return Response(
                    {
                        'status': 'error',
                        'message': 'Failed to initiate STK Push. Please try again.',
                        'error': str(exc),
                        'raw_response': exc.raw_response,
                        'checkout_request_id': payment.checkout_request_id,
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            payment.merchant_request_id = daraja_response.get('MerchantRequestID', '')
            payment.checkout_request_id = daraja_response.get('CheckoutRequestID', '')
            payment.save(update_fields=[
                'merchant_request_id',
                'checkout_request_id',
                'updated_at',
            ])

        return Response({
            'status': 'pending',
            'message': 'STK Push request sent. Enter your M-Pesa PIN to complete.',
            'reference': payment.reference,
            'checkout_request_id': payment.checkout_request_id,
            'merchant_request_id': payment.merchant_request_id,
            'phone_number': phone_number,
            'amount': str(amount),
            'item_type': item_type,
            'item_id': item_id,
            'callback_url': getattr(settings, 'MPESA_CALLBACK_URL', ''),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='status/(?P<checkout_request_id>[^/.]+)')
    def check_status(self, request, checkout_request_id=None):
        """Poll the STK Push status by CheckoutRequestID."""
        if not checkout_request_id:
            return Response(
                {'error': 'checkout_request_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = query_stk_status(checkout_request_id)
        except DarajaAPIError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(result)


@api_view(['POST'])
@permission_classes([])
@csrf_exempt
def mpesa_callback(request):
    """Receive the STK Push callback from Safaricom.

    Safaricom posts a JSON body matching the ``Body.stkCallback`` structure.
    If the result code is ``0`` we credit the user's wallet and record the
    transaction in the ``Transaction`` ledger.
    """
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    logger.info('Daraja callback received: %s', payload)

    callback = (
        payload.get('Body', {})
        .get('stkCallback', {})
    )
    if not callback:
        return JsonResponse({'error': 'Invalid callback structure'}, status=400)

    checkout_request_id = callback.get('CheckoutRequestID', '')
    merchant_request_id = callback.get('MerchantRequestID', '')
    result_code = callback.get('ResultCode', -1)
    result_desc = callback.get('ResultDesc', '')

    try:
        payment = MpesaPayment.objects.get(
            checkout_request_id=checkout_request_id
        )
    except MpesaPayment.DoesNotExist:
        try:
            payment = MpesaPayment.objects.get(
                merchant_request_id=merchant_request_id
            )
        except MpesaPayment.DoesNotExist:
            logger.warning(
                'STK callback for unknown CheckoutRequestID: %s',
                checkout_request_id,
            )
            return JsonResponse({'error': 'Unknown request'}, status=404)

    if result_code == 0:
        metadata = callback.get('CallbackMetadata', {}).get('Item', [])
        receipt = ''
        amount_val = None
        for item in metadata:
            name = item.get('Name', '')
            value = item.get('Value', '')
            if name == 'MpesaReceiptCode':
                receipt = str(value)
            elif name == 'Amount':
                amount_val = value

        with transaction.atomic():
            payment.mark_completed(mpesa_receipt_number=receipt)

            broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(payment.amount)
            total = int(payment.amount)

            txn_desc = f'M-Pesa {payment.get_item_type_display()} #{payment.item_id or "n/a"} (receipt: {receipt})'

            ledger_txn = Transaction.objects.create(
                user=payment.user,
                amount=total,
                broker_fee=broker_fee,
                government_tax=gov_tax,
                category='deposit',
                type='deposit',
                description=txn_desc,
                date=timezone.now(),
            )
            payment.ledger_transaction = ledger_txn
            payment.save(update_fields=['ledger_transaction'])

            record_charges(
                payment.user, 'mpesa_deposit', 'mpesa_deposit', ledger_txn, payment.amount,
                account_number=payment.user.account_number,
                broker_fee=broker_fee, gov_tax=gov_tax,
                broker_rate=broker_rate, tax_rate=tax_rate,
            )

            User.objects.filter(id=payment.user_id).update(
                balance=models.F('balance') + total
            )

        logger.info(
            'STK Push completed: user=%s amount=%s receipt=%s',
            payment.user,
            payment.amount,
            receipt,
        )
    else:
        if result_desc and 'cancel' in result_desc.lower():
            payment.mark_cancelled()
        else:
            payment.mark_failed(code=str(result_code), desc=result_desc)

    return JsonResponse({'status': 'acknowledged'})
