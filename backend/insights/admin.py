from django.contrib import admin

from .models import FinancialAdvice


@admin.register(FinancialAdvice)
class FinancialAdviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'advice_type', 'is_read', 'created_at')
    list_filter = ('advice_type', 'is_read')
    search_fields = ('title', 'message', 'user__username')
