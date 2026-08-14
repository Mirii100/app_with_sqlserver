from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import FinancialAdvice
from .serializers import FinancialAdviceSerializer


class FinancialAdviceViewSet(viewsets.ReadOnlyModelViewSet):
    """Personalised financial advice for the authenticated user."""

    serializer_class = FinancialAdviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialAdvice.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        advice = self.get_object()
        if not advice.is_read:
            advice.is_read = True
            advice.save(update_fields=['is_read'])
        return Response({'status': 'success'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'success'})
