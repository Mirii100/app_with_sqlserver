from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Loan, LoanProduct
from .serializers import LoanSerializer, LoanProductSerializer


from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Loan, LoanProduct
from .serializers import LoanSerializer, LoanProductSerializer
from django_filters.rest_framework import DjangoFilterBackend


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)


class LoanProductViewSet(viewsets.ModelViewSet):
    queryset = LoanProduct.objects.all()
    serializer_class = LoanProductSerializer
    permission_classes = [IsAuthenticated]