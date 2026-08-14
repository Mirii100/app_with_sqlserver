from django.contrib import admin

from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'category', 'subject', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category')
    list_editable = ('status', 'priority')
    search_fields = ('reference', 'subject', 'message', 'user__username')
