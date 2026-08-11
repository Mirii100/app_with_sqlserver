from rest_framework import serializers
from .models import Notification, UserDevice


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'user',
            'title',
            'message',
            'type',
            'is_read',
            'extra_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'updated_at',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'created_at' in data:
            data['created_at'] = instance.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return data


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = [
            'id',
            'user',
            'device_fingerprint',
            'user_agent',
            'ip_address',
            'last_seen',
        ]
        read_only_fields = ['id', 'user', 'last_seen']
