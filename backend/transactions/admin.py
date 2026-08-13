from django.contrib import admin
from .models import Transaction, SavingsGoal, GoalTransaction, Budget, UserLoanLimit


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'type',
        'category',
        'amount',
        'description',
        'date',
        'timestamp',
    )
    list_filter = (
        'type',
        'category',
        'date',
    )
    search_fields = (
        'user__username',
        'user__email',
        'user__phone_number',
        'description',
        'category',
    )
    readonly_fields = ('timestamp',)
    list_select_related = ('user',)
    ordering = ('-date', '-timestamp')
    list_per_page = 25

    date_hierarchy = 'date'


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'user',
        'target_amount',
        'saved_amount',
        'currency',
        'auto_save_enabled',
        'created_at',
    )
    list_filter = (
        'currency',
        'auto_save_enabled',
        'created_at',
    )
    search_fields = (
        'title',
        'purpose',
        'user__username',
        'user__email',
    )
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)
    list_per_page = 25


@admin.register(GoalTransaction)
class GoalTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'savings_goal',
        'user',
        'amount',
        'type',
        'timestamp',
    )
    list_filter = (
        'type',
        'timestamp',
    )
    search_fields = (
        'savings_goal__title',
        'user__username',
        'user__email',
    )
    readonly_fields = ('timestamp',)
    list_select_related = ('savings_goal', 'user')
    list_per_page = 25


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'month',
        'created_at',
    )
    list_filter = (
        'month',
        'created_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'month',
    )
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)
    list_per_page = 25


@admin.register(UserLoanLimit)
class UserLoanLimitAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'limit',
        'used',
        'created_at',
    )
    list_filter = (
        'created_at',
    )
    search_fields = (
        'user__username',
        'user__email',
    )
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user',)
    list_per_page = 25
