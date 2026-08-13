from django.contrib import admin
from .models import User, SecuritySettings


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'full_name',
        'phone_number',
        'account_number',
        'balance',
        'loan_limit',
        'loan_used',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'is_staff',
        'is_active',
        'is_superuser',
        'date_joined',
    )
    search_fields = (
        'username',
        'email',
        'full_name',
        'phone_number',
        'account_number',
    )
    readonly_fields = (
        'account_number',
        'date_joined',
        'last_login',
    )
    fieldsets = (
        (None, {
            'fields': ('username', 'password'),
        }),
        ('Personal Info', {
            'fields': (
                'full_name',
                'email',
                'phone_number',
                'national_id',
                'county',
                'town',
                'postal_code',
                'employment_type',
                'monthly_income',
            ),
        }),
        ('Financial Info', {
            'fields': (
                'account_number',
                'balance',
                'loan_limit',
                'loan_used',
            ),
        }),
        ('Documents', {
            'fields': ('profile_photo', 'id_photo', 'selfie_photo'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )
    ordering = ('-date_joined',)
    list_per_page = 25


@admin.register(SecuritySettings)
class SecuritySettingsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'biometric_enabled',
        'last_pin_changed',
    )
    list_filter = (
        'biometric_enabled',
        'last_pin_changed',
    )
    search_fields = (
        'user__username',
        'user__email',
        'user__phone_number',
    )
    readonly_fields = ('last_pin_changed',)
    list_select_related = ('user',)
    list_per_page = 25
