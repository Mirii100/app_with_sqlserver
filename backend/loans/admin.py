import csv
from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Loan, LoanProduct

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'loan_product', 'amount', 'outstanding_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'loan_product__name')
    
    # Custom view for Ledger
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ledger/', self.admin_site.admin_view(self.ledger_view), name='loans_ledger'),
        ]
        return custom_urls + urls

    def ledger_view(self, request):
        loans = Loan.objects.select_related('user', 'loan_product').all().order_by('-created_at')
        
        ledger_data = [
            {
                'id': l.id,
                'user': l.user.username,
                'product': l.loan_product.name if l.loan_product else 'N/A',
                'amount': l.amount,
                'outstanding': l.outstanding_amount,
                'status': l.status,
                'date': l.created_at,
            }
            for l in loans
        ]

        if request.GET.get('format') == 'pdf':
            html = render_to_string('admin/loans/ledger_pdf.html', {'ledger': ledger_data})
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="loan_ledger.pdf"'
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse('Error generating PDF', status=500)
            return response

        context = self.admin_site.each_context(request)
        context.update({'title': 'Loan Ledger', 'ledger': ledger_data})
        return render(request, 'admin/loans/ledger.html', context)
