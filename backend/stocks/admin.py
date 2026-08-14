import csv
from decimal import Decimal

from django.contrib import admin
from django.db.models import Sum
from django.shortcuts import render
from django.urls import path, reverse
from django.http import HttpResponse

from .models import CompanyRevenue, ShareHolding, Stock, StockWallet


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'sector', 'current_price', 'previous_close', 'is_active')
    list_editable = ('current_price', 'previous_close', 'is_active')
    search_fields = ('code', 'name', 'sector')


@admin.register(StockWallet)
class StockWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'wallet_number', 'balance')
    search_fields = ('user__username', 'wallet_number')


@admin.register(ShareHolding)
class ShareHoldingAdmin(admin.ModelAdmin):
    list_display = ('user', 'stock', 'quantity', 'avg_price')
    search_fields = ('user__username', 'stock__code')


def _money(value):
    return value.quantize(Decimal('0.01')) if value is not None else Decimal('0.00')


@admin.register(CompanyRevenue)
class CompanyRevenueAdmin(admin.ModelAdmin):
    change_list_template = 'admin/stocks/companyrevenue_changelist.html'
    list_display = (
        'company', 'source', 'amount', 'charge_type', 'charge_rate',
        'trade_type', 'total_collected', 'outflow', 'investor_balances_total',
        'user_deposit_balance', 'app_total_charges',
        'total_invested_goals', 'total_invested_chamas',
        'total_invested_stocks', 'account_number', 'transaction_reference',
        'user', 'stock', 'created_at',
    )
    list_filter = ('source', 'trade_type', 'created_at')
    search_fields = ('company', 'account_number', 'user__username', 'stock__code')
    readonly_fields = ('transaction_reference',)
    change_list_template = 'admin/stocks/companyrevenue_changelist.html'

    @admin.display(description='Transaction ref')
    def transaction_reference(self, obj):
        return obj.transaction.reference if obj.transaction else ''

    # Updated get_urls to include the filterable ledger
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('ledger/', self.admin_site.admin_view(self.ledger_view),
                 name='stocks_companyrevenue_ledger'),
        ]
        return custom + urls

    def ledger_view(self, request):
        queryset = CompanyRevenue.objects.all()
        
        # Filtering
        source = request.GET.get('source')
        trade_type = request.GET.get('trade_type')
        if source:
            queryset = queryset.filter(source=source)
        if trade_type:
            queryset = queryset.filter(trade_type=trade_type)
        
        rows = list(queryset.select_related('user', 'stock', 'transaction').order_by('-created_at'))

        if request.GET.get('format') == 'pdf':
            html = render_to_string('admin/stocks/ledger_pdf.html', {'ledger': rows})
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="billing_ledger.pdf"'
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse('Error generating PDF', status=500)
            return response

        context = self.admin_site.each_context(request)
        context.update({
            'title': 'Company Billing Ledger',
            'ledger': rows,
            'source_filter': source,
            'trade_filter': trade_type,
            'sources': CompanyRevenue.objects.values_list('source', flat=True).distinct(),
            'trade_types': CompanyRevenue.objects.values_list('trade_type', flat=True).distinct(),
        })
        return render(request, 'admin/stocks/ledger.html', context)
