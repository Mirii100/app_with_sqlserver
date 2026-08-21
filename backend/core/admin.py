from django.contrib import admin
from django.contrib import messages

from .models import User, SecuritySettings, OtpCode, PaymentQrCode
from . import admin_analytics
from .utils import (
    find_users_with_incomplete_profiles,
    notify_user_incomplete_profile,
)


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
    actions = ['send_profile_completion_notifications']

    @admin.action(
        description='Send profile completion notifications to selected users',
    )
    def send_profile_completion_notifications(self, request, queryset):
        """Send a reminder email (and in-app notification) to each selected
        user that has incomplete profile data."""
        results = find_users_with_incomplete_profiles(queryset)
        sent = 0
        for result in results:
            try:
                if notify_user_incomplete_profile(
                    result.user, result.missing_labels, dry_run=False
                ):
                    sent += 1
            except Exception:
                messages.error(
                    request,
                    f'Failed to notify {result.user.email}',
                )
        total_incomplete = len(results)
        total_selected = queryset.count()
        complete = total_selected - total_incomplete
        messages.success(
            request,
            f'Sent notifications to {sent} user(s) with incomplete '
            f'profiles ({complete} selected user(s) already had '
            f'complete profiles).',
        )


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


@admin.register(PaymentQrCode)
class PaymentQrCodeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'token',
        'is_active',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'user__account_number',
        'token',
    )
    readonly_fields = ('token', 'payload', 'created_at', 'updated_at')
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
