from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Account, Biller, Beneficiary
from .serializers import AccountSerializer, BillerSerializer, BeneficiarySerializer

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

class BillerViewSet(viewsets.ModelViewSet):
    queryset = Biller.objects.all()
    serializer_class = BillerSerializer

class BeneficiaryViewSet(viewsets.ModelViewSet):
    queryset = Beneficiary.objects.all()
    serializer_class = BeneficiarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id is not None:
            return qs.filter(user_id=user_id)
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        account_number = (
            serializer.validated_data.get('account_number')
            or getattr(user, 'account_number', None)
            or ''
        )
        serializer.save(user=user, account_number=account_number)

    def perform_update(self, serializer):
        user = self.request.user
        account_number = (
            serializer.validated_data.get('account_number')
            or getattr(user, 'account_number', None)
            or ''
        )
        serializer.save(user=user, account_number=account_number)
