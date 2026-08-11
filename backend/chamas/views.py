from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Chama, ChamaMembership
from .serializers import ChamaSerializer, ChamaMembershipSerializer

class ChamaViewSet(viewsets.ModelViewSet):
    queryset = Chama.objects.all()
    serializer_class = ChamaSerializer

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        chama = self.get_object()
        user = request.data.get('user')
        if not user:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        membership, created = ChamaMembership.objects.get_or_create(chama=chama, user_id=user)
        
        if created:
            chama.member_count += 1
            chama.save()
            return Response({'status': 'Joined chama'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'Already a member'}, status=status.HTTP_200_OK)

class ChamaMembershipViewSet(viewsets.ModelViewSet):
    queryset = ChamaMembership.objects.all()
    serializer_class = ChamaMembershipSerializer
