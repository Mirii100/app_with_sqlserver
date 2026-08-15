from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny ,IsAuthenticated
from rest_framework.response import Response
from rest_framework import status,generics
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

from .serializers import UserSignupSerializer ,UserSerializer, SecuritySettingsSerializer
from .models import User, SecuritySettings, OtpCode
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
from datetime import timedelta

import logging
import random

from decimal import Decimal, InvalidOperation

from transactions.models import Transaction
from stocks.fees import compute_tiered_charges, record_charges, _money
from .email_utils import email_statement_to_user, email_stock_statement_to_user, email_loan_statement_to_user

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_loan_to_main(request):
    user = request.user

    if user.loan_wallet_balance <= 0:
        return Response({'error': 'No funds in loan wallet'}, status=status.HTTP_400_BAD_REQUEST)

    amount_raw = request.data.get('amount')
    if amount_raw is None or amount_raw == '':
        amount = user.loan_wallet_balance
    else:
        try:
            amount = Decimal(str(amount_raw))
        except (TypeError, ValueError, InvalidOperation):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

    if amount <= 0 or amount > user.loan_wallet_balance:
        return Response({'error': 'Amount exceeds loan wallet balance'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        User.objects.filter(id=user.id).update(
            balance=F('balance') + amount,
            loan_wallet_balance=F('loan_wallet_balance') - amount,
        )
        Transaction.objects.create(
            user=user,
            amount=amount,
            category='loan_wallet_withdrawal',
            type='deposit',
            description='Withdrawal from loan wallet to account',
            date=timezone.now(),
        )

    user.refresh_from_db()
    return Response({
        'message': 'Transfer successful',
        'amount': str(amount),
        'new_balance': str(user.balance),
        'loan_wallet_balance': str(user.loan_wallet_balance),
    })
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_to_chama_wallet(request):
    user = request.user
    amount = Decimal(str(request.data.get('amount', 0)))
    if amount <= 0:
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

    broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(amount)
    total_deduction = _money(amount + broker_fee + gov_tax)

    if user.balance < total_deduction:
        return Response(
            {'error': f'Insufficient funds. KSh {_money(broker_fee + gov_tax)} in charges apply.',
             'broker_fee': str(broker_fee),
             'government_tax': str(gov_tax),
             'total_charges': str(_money(broker_fee + gov_tax))},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        txn = Transaction.objects.create(
            user=user,
            amount=total_deduction,
            category='chama_wallet_funding',
            type='withdrawal',
            description=f'Transfer to chama wallet (KSh {amount} + charges KSh {_money(broker_fee + gov_tax)})',
            date=timezone.now(),
        )
        User.objects.filter(id=user.id).update(
            balance=F('balance') - total_deduction,
            chama_wallet_balance=F('chama_wallet_balance') + amount,
        )
        record_charges(
            user, 'chama_wallet_funding', 'chama_wallet_funding', txn, amount,
            account_number=user.account_number,
            broker_fee=broker_fee, gov_tax=gov_tax,
            broker_rate=broker_rate, tax_rate=tax_rate,
        )

    user.refresh_from_db()
    return Response({
        'message': 'Transfer to Chama wallet successful',
        'amount': str(amount),
        'new_balance': str(user.balance),
        'chama_wallet': str(user.chama_wallet_balance),
        'broker_fee': str(broker_fee),
        'government_tax': str(gov_tax),
        'total_charges': str(_money(broker_fee + gov_tax)),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_to_goal_wallet(request):
    user = request.user
    amount = Decimal(str(request.data.get('amount', 0)))
    if amount <= 0:
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

    broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(amount)
    total_deduction = _money(amount + broker_fee + gov_tax)

    if user.balance < total_deduction:
        return Response(
            {'error': f'Insufficient funds. KSh {_money(broker_fee + gov_tax)} in charges apply.',
             'broker_fee': str(broker_fee),
             'government_tax': str(gov_tax),
             'total_charges': str(_money(broker_fee + gov_tax))},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        txn = Transaction.objects.create(
            user=user,
            amount=total_deduction,
            category='goal_wallet_funding',
            type='withdrawal',
            description=f'Transfer to goal wallet (KSh {amount} + charges KSh {_money(broker_fee + gov_tax)})',
            date=timezone.now(),
        )
        User.objects.filter(id=user.id).update(
            balance=F('balance') - total_deduction,
            goal_wallet_balance=F('goal_wallet_balance') + amount,
        )
        record_charges(
            user, 'goal_wallet_funding', 'goal_wallet_funding', txn, amount,
            account_number=user.account_number,
            broker_fee=broker_fee, gov_tax=gov_tax,
            broker_rate=broker_rate, tax_rate=tax_rate,
        )

    user.refresh_from_db()
    return Response({
        'message': 'Transfer to Goal wallet successful',
        'amount': str(amount),
        'new_balance': str(user.balance),
        'goal_wallet': str(user.goal_wallet_balance),
        'broker_fee': str(broker_fee),
        'government_tax': str(gov_tax),
        'total_charges': str(_money(broker_fee + gov_tax)),
    })

from notifications.models import UserDevice, Notification

def _attach_image(user, attr, fileobj):
    if fileobj:
        getattr(user, attr).save(fileobj.name, fileobj, save=False)

def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    serializer = UserSignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        _attach_image(user, 'profile_photo', request.data.get('profile_photo'))
        _attach_image(user, 'id_photo', request.data.get('id_photo'))
        _attach_image(user, 'selfie_photo', request.data.get('selfie_photo'))
        user.save()

        SecuritySettings.objects.get_or_create(user=user)

        from rewards.points import award_points

        referrer = None
        referral_code = (request.data.get('referral_code') or '').strip().upper()
        if referral_code:
            referrer = User.objects.filter(referral_code=referral_code).exclude(id=user.id).first()
            if referrer:
                user.referred_by = referrer
                user.save(update_fields=['referred_by'])
                award_points(
                    referrer,
                    'referral',
                    key=f'referral:{referrer.id}:{user.id}',
                    description=f'You referred {user.full_name or user.username}',
                )

        award_points(
            user,
            'signup',
            key=f'signup:{user.id}',
            description='Welcome bonus',
            notify=False,
        )

        user.refresh_from_db()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'full_name': user.get_full_name() or user.username,
            'phone': user.phone_number,
            'account_number': user.account_number,
            'referral_code': user.referral_code,
            'points': user.points,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    device_fingerprint = request.data.get('device_fingerprint')
    device_name = request.data.get('device_name', '')
    user_agent = request.META.get('HTTP_USER_AGENT', device_name)
    ip_address = _get_client_ip(request)

    user = authenticate(username=email, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)

        # Track device / detect new login
        if device_fingerprint:
            existing_device = UserDevice.objects.filter(
                user=user,
                device_fingerprint=device_fingerprint,
            ).first()

            if not existing_device:
                UserDevice.objects.create(
                    user=user,
                    device_fingerprint=device_fingerprint,
                    user_agent=user_agent,
                    ip_address=ip_address,
                )

                location_hint = request.data.get('location', '')
                message_parts = [device_name] if device_name else []
                if location_hint:
                    message_parts.append(location_hint)

                subtitle = ' · '.join(message_parts) if message_parts else 'New device'
                Notification.objects.create(
                    user=user,
                    title='New device login',
                    message=subtitle,
                    type='new_device_login',
                    extra_data={
                        'device_name': device_name,
                        'location': location_hint,
                        'ip_address': ip_address,
                    },
                )

        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'full_name': user.get_full_name() or user.username,
            'phone': user.phone_number,
            'account_number': user.account_number,
        })
    return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user_id = request.data.get('user_id')
    new_password = request.data.get('new_password')

    if user_id is None or request.user.id != int(user_id):
        return Response({'error': 'Cannot change password for another user'}, status=status.HTTP_403_FORBIDDEN)

    if not new_password or len(str(new_password)) < 6:
        return Response({'error': 'New password must be at least 6 characters'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    user.set_password(new_password)
    user.save(update_fields=['password'])

    return Response({
        'message': 'Password updated successfully',
    }, status=status.HTTP_200_OK)

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class SecuritySettingsViewSet(viewsets.ModelViewSet):
    queryset = SecuritySettings.objects.all()
    serializer_class = SecuritySettingsSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()


OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _generate_otp_code():
    """Return a random 6-digit string."""
    return f"{random.randint(0, 999999):06d}"


def _mask_destination(identifier, channel):
    """Mask a contact for display, e.g. u***@example.com or +254*****123."""
    identifier = str(identifier or '')
    if channel == 'email':
        if '@' not in identifier:
            return identifier
        local, domain = identifier.split('@', 1)
        if not local:
            return identifier
        if len(local) <= 2:
            masked_local = local[0] + '***'
        else:
            masked_local = local[0] + '***' + local[-1]
        return f"{masked_local}@{domain}"
    # Phone
    if len(identifier) <= 4:
        return '****' + identifier
    return identifier[:3] + '*' * (len(identifier) - 3) + identifier[-3:]


def _send_otp_email(email, code, expires_at):
    subject = 'Your Alexia verification code'
    message = (
        f'Your Alexia verification code is {code}.\n\n'
        f'It expires in {OTP_EXPIRY_MINUTES} minutes. If you did not '
        f'request this code, you can safely ignore this email.\n\n'
        f'— Alexia Financials'
    )
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning('Failed to send OTP email to %s: %s', email, e)


def _send_otp_sms(phone_number, code, expires_at):
    """Send the OTP via SMS.

    No SMS provider is configured yet, so the code is logged to the server
    console (and lands in server_out.log). Wire this up to a real gateway
    (e.g. Africa's Talking, Twilio) by replacing the body of this function.
    """
    logger.info('[SMS OTP] To %s -> Your Alexia verification code is %s. '
                'It expires in %s minutes.', phone_number, code, OTP_EXPIRY_MINUTES)


def _lookup_user(identifier):
    if not identifier:
        return None
    return (
        User.objects.filter(username__iexact=identifier).first()
        or User.objects.filter(email__iexact=identifier).first()
        or User.objects.filter(phone_number=identifier).first()
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    identifier = request.data.get('email') or request.data.get('phone')
    channel = (request.data.get('channel') or 'email').lower()
    purpose = (request.data.get('purpose') or 'login').lower()

    if not identifier:
        return Response(
            {'error': 'Email or phone number is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if channel not in ('email', 'phone'):
        return Response(
            {'error': 'Channel must be either "email" or "phone".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = _lookup_user(identifier)
    if user is None:
        return Response(
            {'error': 'No account found for the provided contact.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    code = _generate_otp_code()
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Invalidate any previous unused codes for this user+channel+purpose so
    # only the latest OTP is ever valid.
    OtpCode.objects.filter(
        user=user,
        channel=channel,
        purpose=purpose,
        is_used=False,
    ).update(is_used=True)

    destination = user.email if channel == 'email' else user.phone_number

    OtpCode.objects.create(
        user=user,
        code_hash=make_password(code),
        channel=channel,
        purpose=purpose,
        destination=destination,
        expires_at=expires_at,
    )

    if channel == 'email':
        _send_otp_email(user.email, code, expires_at)
    else:
        _send_otp_sms(user.phone_number, code, expires_at)

    return Response({
        'message': 'OTP sent successfully.',
        'channel': channel,
        'destination': _mask_destination(destination, channel),
        'expires_in': OTP_EXPIRY_MINUTES * 60,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    identifier = request.data.get('email') or request.data.get('phone')
    code = request.data.get('code')
    channel = (request.data.get('channel') or 'email').lower()
    purpose = (request.data.get('purpose') or 'login').lower()
    device_fingerprint = request.data.get('device_fingerprint')
    device_name = request.data.get('device_name', '')
    user_agent = request.META.get('HTTP_USER_AGENT', device_name)
    ip_address = _get_client_ip(request)

    if not identifier or not code:
        return Response(
            {'error': 'Contact and code are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = str(code).strip()
    if not (code.isdigit() and len(code) == 6):
        return Response(
            {'error': 'OTP must be a 6-digit number.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = _lookup_user(identifier)
    if user is None:
        return Response(
            {'error': 'Invalid contact or code.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp = OtpCode.objects.filter(
        user=user,
        channel=channel,
        purpose=purpose,
        is_used=False,
    ).order_by('-created_at').first()

    if otp is None:
        return Response(
            {'error': 'No active OTP. Please request a new code.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if otp.attempts >= OTP_MAX_ATTEMPTS:
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        return Response(
            {'error': 'Too many failed attempts. Please request a new code.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if otp.expires_at < timezone.now():
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        return Response(
            {'error': 'This code has expired. Please request a new one.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not otp.is_valid_code(code):
        OtpCode.objects.filter(id=otp.id).update(attempts=F('attempts') + 1)
        return Response(
            {'error': 'Invalid OTP. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp.is_used = True
    otp.save(update_fields=['is_used'])

    token, created = Token.objects.get_or_create(user=user)

    if device_fingerprint:
        _track_new_device(request, user, device_fingerprint, device_name,
                          user_agent, ip_address)

    return Response({
        'token': token.key,
        'user_id': user.id,
        'email': user.email,
        'full_name': user.get_full_name() or user.username,
        'phone': user.phone_number,
        'account_number': user.account_number,
    }, status=status.HTTP_200_OK)


def _track_new_device(request, user, device_fingerprint, device_name,
                      user_agent, ip_address):
    existing_device = UserDevice.objects.filter(
        user=user,
        device_fingerprint=device_fingerprint,
    ).first()

    if existing_device:
        return

    UserDevice.objects.create(
        user=user,
        device_fingerprint=device_fingerprint,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    location_hint = request.data.get('location', '')
    message_parts = [device_name] if device_name else []
    if location_hint:
        message_parts.append(location_hint)

    subtitle = ' · '.join(message_parts) if message_parts else 'New device'
    Notification.objects.create(
        user=user,
        title='New device login',
        message=subtitle,
        type='new_device_login',
        extra_data={
            'device_name': device_name,
            'location': location_hint,
            'ip_address': ip_address,
        },
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def email_statement(request):
    """Email the authenticated user's account statement as a PDF attachment."""
    user = request.user

    if not user.email:
        return Response(
            {'error': 'No email address on file. Update your profile first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ok = email_statement_to_user(user)
    if not ok:
        return Response(
            {'error': 'Failed to send your statement. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    Notification.objects.create(
        user=user,
        title='Account statement sent',
        message=f'Your account statement was emailed to {user.email}.',
        type='general',
    )

    return Response({'message': f'Statement sent to {user.email}.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def email_stock_statement(request):
    """Email the authenticated user's shares statement as a PDF attachment."""
    from stocks.models import ShareHolding

    user = request.user

    if not user.email:
        return Response(
            {'error': 'No email address on file. Update your profile first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not ShareHolding.objects.filter(user=user).exists():
        return Response(
            {'error': 'No shares in your portfolio to send a statement for.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ok = email_stock_statement_to_user(user)
    if not ok:
        return Response(
            {'error': 'Failed to send your statement. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    Notification.objects.create(
        user=user,
        title='Shares statement sent',
        message=f'Your shares statement was emailed to {user.email}.',
        type='general',
    )

    return Response({'message': f'Shares statement sent to {user.email}.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def email_loan_statement(request):
    """Email the authenticated user's loan statement as a PDF attachment."""
    from loans.models import Loan

    user = request.user

    if not user.email:
        return Response(
            {'error': 'No email address on file. Update your profile first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not Loan.objects.filter(user=user).exists():
        return Response(
            {'error': 'No loans on this account to send a statement for.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ok = email_loan_statement_to_user(user)
    if not ok:
        return Response(
            {'error': 'Failed to send your statement. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    Notification.objects.create(
        user=user,
        title='Loan statement sent',
        message=f'Your loan statement was emailed to {user.email}.',
        type='general',
    )

    return Response({'message': f'Loan statement sent to {user.email}.'})