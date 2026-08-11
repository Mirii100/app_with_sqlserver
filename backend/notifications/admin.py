from django.contrib import admin
from .models import Notification, UserDevice


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    date_hierarchy = 'created_at'

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected as read"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected as unread"

    actions = [mark_as_read, mark_as_unread]


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'device_fingerprint', 'ip_address', 'last_seen']
    search_fields = ['user__username', 'device_fingerprint', 'ip_address']
    date_hierarchy = 'last_seen'
