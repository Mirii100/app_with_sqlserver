from django.contrib import admin
from .models import User, SecuritySettings, OtpCode
from . import admin_analytics

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
        'points',
        'referral_code',
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
        'referral_code',
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
                'points',
                'loan_limit',
                'loan_used',
            ),
        }),
        ('Referral', {
            'fields': ('referral_code', 'referred_by'),
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


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'channel',
        'purpose',
        'destination',
        'is_used',
        'attempts',
        'created_at',
        'expires_at',
    )
    list_filter = (
        'channel',
        'purpose',
        'is_used',
    )
    search_fields = (
        'user__username',
        'user__email',
        'user__phone_number',
        'destination',
    )
    readonly_fields = (
        'code_hash',
        'created_at',
        'expires_at',
    )
    list_select_related = ('user',)
    list_per_page = 25
