from django.contrib import admin
from .models import Account, Biller, Beneficiary


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'account_number',
        'user',
        'account_type',
        'currency',
        'balance',
        'available_balance',
        'status',
        'created_at',
    )
    list_filter = (
        'account_type',
        'currency',
        'status',
        'created_at',
    )
    search_fields = (
        'account_number',
        'user__username',
        'user__email',
        'user__phone_number',
    )
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)
    ordering = ('-created_at',)
    list_per_page = 25


@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'user',
        'category',
        'account_number',
        'title',
        'subtitle',
    )
    list_filter = (
        'category',
    )
    search_fields = (
        'name',
        'title',
        'subtitle',
        'account_number',
        'user__username',
        'user__email',
        'user__phone_number',
    )
    list_select_related = ('user',)
    list_per_page = 25


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'user',
        'phone_number',
        'account_number',
        'bank_name',
        'is_bank',
        'created_at',
    )
    list_filter = (
        'is_bank',
        'created_at',
    )
    search_fields = (
        'name',
        'phone_number',
        'account_number',
        'bank_name',
        'user__username',
        'user__email',
        'user__phone_number',
    )
    list_select_related = ('user',)
    ordering = ('name',)
    list_per_page = 25
