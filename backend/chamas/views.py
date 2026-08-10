from rest_framework import viewsets
from .models import Chama, ChamaMembership
from .serializers import ChamaSerializer, ChamaMembershipSerializer

class ChamaViewSet(viewsets.ModelViewSet):
    queryset = Chama.objects.all()
    serializer_class = ChamaSerializer

class ChamaMembershipViewSet(viewsets.ModelViewSet):
    queryset = ChamaMembership.objects.all()
    serializer_class = ChamaMembershipSerializer
