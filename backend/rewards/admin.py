from django.contrib import admin

from .models import Reward, RewardTransaction


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_cost', 'icon', 'is_active')
    list_editable = ('points_cost', 'is_active')
    search_fields = ('name',)


@admin.register(RewardTransaction)
class RewardTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'reward', 'points_cost', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'reward__name')
