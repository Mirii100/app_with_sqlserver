import csv
import random
import string
from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from datetime import datetime, timedelta
from .models import Account, CreditCard, DebitCard, UserCardSettings


def generate_cvv():
    """Generate a random 3-digit CVV."""
    return ''.join(random.choices(string.digits, k=3))


def _change_status(modeladmin, request, queryset, status, label):
    count = 0
    for obj in queryset:
        obj.status = status
        obj.save(update_fields=['status'])
        count += 1
    modeladmin.message_user(request, f'{count} card(s) {label}.')


def make_active(modeladmin, request, queryset):
    _change_status(modeladmin, request, queryset, CreditCard.Status.ACTIVE, 'activated')
make_active.short_description = 'Mark selected cards as active'


def make_frozen(modeladmin, request, queryset):
    _change_status(modeladmin, request, queryset, CreditCard.Status.FROZEN, 'frozen')
make_frozen.short_description = 'Freeze selected cards'


def make_blocked(modeladmin, request, queryset):
    _change_status(modeladmin, request, queryset, CreditCard.Status.BLOCKED, 'blocked')
make_blocked.short_description = 'Block selected cards'

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


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ('masked', 'user', 'account_number', 'card_type', 'status', 'spend_limit')
    list_filter = ('card_type', 'status')
    search_fields = ('card_number', 'cardholder_name', 'account_number')
    actions = [make_active, make_frozen, make_blocked]

    @admin.display(description='Card')
    def masked(self, obj):
        return obj.mask_card_number()

    def get_form(self, request, obj=None, **kwargs):
        """Customize form for add and change views."""
        if obj is None:
            # Add view - only show cardholder_name and reason_for_applying
            self.add_form = None  # We'll use a custom approach
            from django import forms
            from .models import CreditCard
            
            class AddCardForm(forms.ModelForm):
                class Meta:
                    model = CreditCard
                    fields = ['cardholder_name', 'reason_for_applying']
                    
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    # Set expiry_date and cvv as hidden/system-generated
                    if self.instance.pk:
                        self.fields['expiry_date'] = forms.CharField(
                            initial=self.instance.expiry_date, disabled=True)
                        self.fields['cvv'] = forms.CharField(
                            initial=self.instance.cvv, disabled=True)
                    else:
                        # Generate CVV for new card
                        self.fields['cvv'] = forms.CharField(
                            initial=generate_cvv(), disabled=True)
                        # Set expiry_date to 3 years from now
                        today = datetime.now()
                        exp_date = today + timedelta(days=3*365)
                        self.fields['expiry_date'] = forms.CharField(
                            initial=exp_date.strftime('%m/%y'), disabled=True)
            
            self.add_form = AddCardForm
        return super().get_form(request, obj, **kwargs)


@admin.register(DebitCard)
class DebitCardAdmin(admin.ModelAdmin):
    list_display = ('masked', 'user', 'account_number', 'card_type', 'status', 'spend_limit')
    list_filter = ('card_type', 'status')
    search_fields = ('card_number', 'cardholder_name', 'account_number')
    actions = [make_active, make_frozen, make_blocked]

    @admin.display(description='Card')
    def masked(self, obj):
        return obj.mask_card_number()

    def get_form(self, request, obj=None, **kwargs):
        """Customize form for add and change views."""
        if obj is None:
            # Add view - only show cardholder_name and reason_for_applying
            from django import forms
            from .models import DebitCard
            
            class AddCardForm(forms.ModelForm):
                class Meta:
                    model = DebitCard
                    fields = ['cardholder_name', 'reason_for_applying']
                    
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    # Set expiry_date and cvv as hidden/system-generated
                    if self.instance.pk:
                        self.fields['expiry_date'] = forms.CharField(
                            initial=self.instance.expiry_date, disabled=True)
                        self.fields['cvv'] = forms.CharField(
                            initial=self.instance.cvv, disabled=True)
                    else:
                        # Generate CVV for new card
                        self.fields['cvv'] = forms.CharField(
                            initial=generate_cvv(), disabled=True)
                        # Set expiry_date to 3 years from now
                        today = datetime.now()
                        exp_date = today + timedelta(days=3*365)
                        self.fields['expiry_date'] = forms.CharField(
                            initial=exp_date.strftime('%m/%y'), disabled=True)
            
            self.add_form = AddCardForm
        return super().get_form(request, obj, **kwargs)


@admin.register(UserCardSettings)
class UserCardSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'online_payments_enabled', 'contactless_enabled')
    list_filter = ('online_payments_enabled', 'contactless_enabled')
    search_fields = ('user__email', 'user__username')


