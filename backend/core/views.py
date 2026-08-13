from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny ,IsAuthenticated
from rest_framework.response import Response
from rest_framework import status,generics
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

from .serializers import UserSignupSerializer ,UserSerializer, SecuritySettingsSerializer
from .models import User, SecuritySettings
from django.db import transaction

from decimal import Decimal
from django.db import transaction

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_loan_to_main(request):
    user = request.user
    
    if user.loan_wallet_balance <= 0:
        return Response({'error': 'No funds in loan wallet'}, status=status.HTTP_400_BAD_REQUEST)
        
    amount = user.loan_wallet_balance
    
    with transaction.atomic():
        user.balance += amount
        user.loan_wallet_balance = 0
        user.save()
        
    return Response({'message': 'Transfer successful', 'new_balance': user.balance})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_to_chama_wallet(request):
    user = request.user
    amount = Decimal(request.data.get('amount', 0))
    
    if amount <= 0 or user.balance < amount:
        return Response({'error': 'Insufficient funds or invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
    with transaction.atomic():
        user.balance -= amount
        user.chama_wallet_balance += amount
        user.save()
        
    return Response({'message': 'Transfer to Chama wallet successful', 'new_balance': user.balance, 'chama_wallet': user.chama_wallet_balance})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_to_goal_wallet(request):
    user = request.user
    amount = Decimal(request.data.get('amount', 0))
    
    if amount <= 0 or user.balance < amount:
        return Response({'error': 'Insufficient funds or invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
    with transaction.atomic():
        user.balance -= amount
        user.goal_wallet_balance += amount
        user.save()
        
    return Response({'message': 'Transfer to Goal wallet successful', 'new_balance': user.balance, 'goal_wallet': user.goal_wallet_balance})


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

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'full_name': user.get_full_name() or user.username,
            'phone': user.phone_number,
            'account_number': user.account_number,
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