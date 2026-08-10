from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny ,IsAuthenticated
from rest_framework.response import Response
from rest_framework import status,generics
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

from .serializers import UserSignupSerializer ,UserSerializer
from .models import User

def _attach_image(user, attr, fileobj):
    if fileobj:
        getattr(user, attr).save(fileobj.name, fileobj, save=False)

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
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'full_name': user.get_full_name() or user.username,
            'phone': user.phone_number,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(username=email, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'email': user.email,
            'full_name': user.get_full_name() or user.username,
            'phone': user.phone_number,
        })
    return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]