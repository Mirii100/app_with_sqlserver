from rest_framework import serializers

from .models import SupportTicket


class SupportTicketSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'reference',
            'category',
            'category_display',
            'subject',
            'message',
            'priority',
            'priority_display',
            'status',
            'status_display',
            'resolution_note',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'reference',
            'status',
            'resolution_note',
            'created_at',
            'updated_at',
        ]
