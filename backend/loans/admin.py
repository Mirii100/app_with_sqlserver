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