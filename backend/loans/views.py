from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Loan, LoanProduct
from .serializers import LoanSerializer, LoanProductSerializer


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]


class LoanProductViewSet(viewsets.ModelViewSet):
    queryset = LoanProduct.objects.all()
    serializer_class = LoanProductSerializer
    permission_classes = [IsAuthenticated]