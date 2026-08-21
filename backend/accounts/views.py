from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Account, CreditCard, DebitCard, UserCardSettings
from .serializers import AccountSerializer, CreditCardSerializer, DebitCardSerializer, UserCardSettingsSerializer


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id is not None:
            return qs.filter(user_id=user_id)
        return qs.filter(user=self.request.user)


class CreditCardViewSet(viewsets.ModelViewSet):
    """ViewSet for Credit Card CRUD operations."""
    
    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'status', 'card_type']
    
    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id is not None:
            return qs.filter(user_id=user_id)
        return qs.filter(user=self.request.user)


class DebitCardViewSet(viewsets.ModelViewSet):
    """ViewSet for Debit Card CRUD operations."""
    
    queryset = DebitCard.objects.all()
    serializer_class = DebitCardSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'status', 'card_type']
    
    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id is not None:
            return qs.filter(user_id=user_id)
        return qs.filter(user=self.request.user)


class UserCardSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for User Card Settings."""
    
    queryset = UserCardSettings.objects.all()
    serializer_class = UserCardSettingsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']
    
    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id is not None:
            return qs.filter(user_id=user_id)
        return qs.filter(user=self.request.user)