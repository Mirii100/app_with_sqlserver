from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.db.models import Sum
from decimal import Decimal
from accounts.models import Account
from investments.models import InvestmentWallet
from loans.models import Loan
from stocks.models import StockWallet
from .models import AnalyticsDashboard

@admin.register(AnalyticsDashboard)
class BusinessAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = 'admin/core/businessanalytics_changelist.html'

    def changelist_view(self, request, extra_context=None):
        return redirect('admin:business_performance')

    def get_urls(self):
        return [
            path('performance/', self.admin_site.admin_view(self.performance_view), name='business_performance'),
            path('liquidity/', self.admin_site.admin_view(self.liquidity_view), name='liquidity_report'),
        ] + super().get_urls()

    def performance_view(self, request):
        accounts = Account.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal(0)
        investments = InvestmentWallet.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal(0)
        loans = Loan.objects.aggregate(Sum('outstanding_amount'))['outstanding_amount__sum'] or Decimal(0)
        stocks = StockWallet.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal(0)
        total = accounts + investments + loans + stocks
        data = {
            'Accounts': float(accounts),
            'Investments': float(investments),
            'Loans': float(loans),
            'Stocks': float(stocks),
        }
        context = self.admin_site.each_context(request)
        context.update({'title': 'Business Performance', 'data': data, 'total': float(total)})
        return render(request, 'admin/business_analytics/performance.html', context)

    def liquidity_view(self, request):
        liquid_assets = Account.objects.aggregate(Sum('balance'))['balance__sum'] or Decimal(0)
        context = self.admin_site.each_context(request)
        context.update({'title': 'Liquidity Report', 'liquid_assets': float(liquid_assets)})
        return render(request, 'admin/business_analytics/liquidity.html', context)
