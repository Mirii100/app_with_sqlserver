import csv
from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Account, Biller

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_number', 'account_type', 'balance', 'status')
    change_list_template = 'admin/accounts/account_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ledger/', self.admin_site.admin_view(self.ledger_view), name='accounts_ledger'),
            path('report/', self.admin_site.admin_view(self.report_view), name='accounts_report'),
        ]
        return custom_urls + urls

    def report_view(self, request):
        from django.db.models import Sum
        accounts = Account.objects.all()
        by_type = accounts.values('account_type').annotate(total=Sum('balance'))
        
        context = self.admin_site.each_context(request)
        context.update({
            'title': 'Account Analytics',
            'by_type': list(by_type),
        })
        return render(request, 'admin/accounts/report.html', context)

    def ledger_view(self, request):
        # Fetch accounts and related transactions
        accounts = Account.objects.select_related('user').all()
        
        # Build ledger data
        ledger_data = []
        for acc in accounts:
            transactions = acc.user.transactions.all().order_by('-date')
            for txn in transactions:
                ledger_data.append({
                    'date': txn.date,
                    'account_number': acc.account_number,
                    'user': acc.user.username,
                    'type': txn.type,
                    'category': txn.category,
                    'amount': txn.amount,
                    'broker_fee': txn.broker_fee,
                    'government_tax': txn.government_tax,
                    'description': txn.description,
                })

        if request.GET.get('format') == 'pdf':
            html = render_to_string('admin/accounts/ledger_pdf.html', {'ledger': ledger_data})
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="ledger.pdf"'
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse('Error generating PDF', status=500)
            return response

        context = self.admin_site.each_context(request)
        context.update({
            'title': 'Account Transaction Ledger',
            'ledger': ledger_data,
        })
        return render(request, 'admin/accounts/ledger.html', context)

@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_number', 'balance', 'category')
