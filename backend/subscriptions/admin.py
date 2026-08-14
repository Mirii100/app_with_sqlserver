from django.contrib import admin

from .models import Subscription, SubscriptionWallet, UserSubscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'price',
        'billing_cycle',
        'active',
        'created_at',
    )
    list_filter = (
        'active',
        'billing_cycle',
    )
    search_fields = (
        'name',
        'description',
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'subscription',
        'status',
        'subscribed_at',
    )
    list_filter = (
        'status',
        'subscribed_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'subscription__name',
    )
    list_select_related = ('user', 'subscription')
    list_per_page = 25


@admin.register(SubscriptionWallet)
class SubscriptionWalletAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'account_number',
        'balance',
        'currency',
        'created_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'account_number',
    )
    list_select_related = ('user',)
    list_per_page = 25
