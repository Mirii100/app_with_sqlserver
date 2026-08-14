from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Transaction, SavingsGoal, GoalTransaction, Budget, UserLoanLimit
from core.admin_utils import ExportCsvMixin


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin, ExportCsvMixin):
    change_list_template = 'admin/transactions/transaction_changelist.html'
    list_display = (
        'id', 'reference', 'user', 'type', 'category', 'amount', 'broker_fee', 'government_tax', 'date',
    )
    list_filter = ('type', 'category', 'date')
    search_fields = ('user__username', 'reference', 'description')
    readonly_fields = ('timestamp',)
    actions = ['export_as_csv']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('ledger/', self.admin_site.admin_view(self.ledger_view), name='transactions_ledger'),
        ]
        return custom + urls

    def ledger_view(self, request):
        queryset = Transaction.objects.all()
        
        # Filtering
        txn_type = request.GET.get('type')
        category = request.GET.get('category')
        if txn_type:
            queryset = queryset.filter(type=txn_type)
        if category:
            queryset = queryset.filter(category=category)
        
        rows = list(queryset.select_related('user').order_by('-date'))

        if request.GET.get('format') == 'pdf':
            html = render_to_string('admin/transactions/ledger_pdf.html', {'ledger': rows})
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="transaction_ledger.pdf"'
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse('Error generating PDF', status=500)
            return response

        context = self.admin_site.each_context(request)
        context.update({
            'title': 'Transaction Ledger',
            'ledger': rows,
            'type_filter': txn_type,
            'cat_filter': category,
            'types': Transaction.objects.values_list('type', flat=True).distinct(),
            'categories': Transaction.objects.values_list('category', flat=True).distinct(),
        })
        return render(request, 'admin/transactions/ledger.html', context)


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
        'reference',
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
        'reference',
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
