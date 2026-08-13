from django.contrib import admin
from .models import Chama, ChamaMembership


@admin.register(Chama)
class ChamaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'admin',
        'member_count',
        'target_amount',
        'monthly_contribution',
        'contribution_frequency',
        'total_pool_balance',
        'status',
        'invite_code',
        'created_at',
    )
    list_filter = (
        'status',
        'contribution_frequency',
        'created_at',
    )
    search_fields = (
        'name',
        'description',
        'invite_code',
        'admin__username',
        'admin__email',
        'admin__phone_number',
    )
    readonly_fields = (
        'invite_code',
        'created_at',
        'updated_at',
    )
    list_select_related = ('admin',)
    ordering = ('-created_at',)
    list_per_page = 25


@admin.register(ChamaMembership)
class ChamaMembershipAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'chama',
        'user',
        'role',
        'joined_at',
    )
    list_filter = (
        'role',
        'joined_at',
    )
    search_fields = (
        'chama__name',
        'chama__invite_code',
        'user__username',
        'user__email',
        'user__phone_number',
    )
    readonly_fields = ('joined_at',)
    list_select_related = ('chama', 'user')
    ordering = ('-joined_at',)
    list_per_page = 25
