from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Loan, LoanProduct


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'user',
        'is_best_match',
        'is_outline',
        'created_at',
    )

    search_fields = (
        'name',
        'description',
    )

    list_filter = (
        'is_best_match',
        'is_outline',
    )


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'loan_product',
        'amount',
        'outstanding_amount',
        'status',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'purpose',
    )

    list_filter = (
        'status',
    )

    actions = ['approve_loans', 'reject_loans', 'cancel_loans']

    @admin.action(description='Approve selected loans')
    def approve_loans(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description='Reject selected loans')
    def reject_loans(self, request, queryset):
        queryset.update(status='rejected')

    @admin.action(description='Cancel selected loans')
    def cancel_loans(self, request, queryset):
        queryset.update(status='cancelled')