from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Investment, InvestmentProduct, InvestmentWallet

@admin.register(InvestmentProduct)
class InvestmentProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'annual_rate', 'is_active')

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'amount', 'net_payout', 'status', 'invested_at')
    list_filter = ('status', 'invested_at')
    
    # Custom view for Ledger
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ledger/', self.admin_site.admin_view(self.ledger_view), name='investments_ledger'),
        ]
        return custom_urls + urls

    def ledger_view(self, request):
        investments = Investment.objects.select_related('user', 'product').all().order_by('-invested_at')
        
        ledger_data = [
            {
                'date': i.invested_at,
                'user': i.user.username,
                'product': i.product.name,
                'amount': i.amount,
                'maturity_value': i.maturity_value,
                'fee': i.fee_deducted,
                'payout': i.net_payout,
                'status': i.status,
            }
            for i in investments
        ]

        if request.GET.get('format') == 'pdf':
            html = render_to_string('admin/investments/ledger_pdf.html', {'ledger': ledger_data})
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="investment_ledger.pdf"'
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse('Error generating PDF', status=500)
            return response

        context = self.admin_site.each_context(request)
        context.update({'title': 'Investment Ledger', 'ledger': ledger_data})
        return render(request, 'admin/investments/ledger.html', context)

@admin.register(InvestmentWallet)
class InvestmentWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_type', 'balance')
