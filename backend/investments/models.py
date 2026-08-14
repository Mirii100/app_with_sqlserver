from decimal import Decimal, ROUND_HALF_UP
import random
import string

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from transactions.models import Transaction


def _money(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# Distinguishing prefix per product type so wallet numbers are easily
# recognizable in the database/admin:
#   treasury_bill          -> 5XXXXXXXXXXX
#   money_market_fund      -> 6XXXXXXXXXXX
#   balanced_unit_trust    -> 7XXXXXXXXXXX
_WALLET_PREFIXES = {
    'treasury_bill': '5',
    'money_market_fund': '6',
    'balanced_unit_trust': '7',
}


def generate_wallet_number(product_type):
    """Generate a unique 12-digit wallet number, distinguishable per type."""
    prefix = _WALLET_PREFIXES.get(product_type, '8')
    while True:
        number = prefix + ''.join(random.choices(string.digits, k=11))
        if not InvestmentWallet.objects.filter(wallet_number=number).exists():
            return number


def compute_investment(amount, product):
    """Compute the payout for an investment, deducting a fee before the
    investor is paid.

    Treasury bill (Kenya / CBK convention, 365-day basis):
        Price = Face / (1 + r * d / 365)   ->   Face = amount * (1 + r * d / 365)
        The discount (Face - Price) is the interest earned. A service fee of
        `fee_percent` of the invested amount is deducted before payout.

    Money market fund (open-ended):
        No fixed maturity and no upfront deduction. Interest is computed and
        deposited daily at the net (after-fee) annual rate:
            daily rate = (annual_rate - fee_percent) / 100 / 365
        The investor can redeem any time; the payout is principal plus the
        interest accrued so far.

    Balanced unit trust (fixed term):
        The annual management fee reduces the gross annual rate to a net rate.
        Value grows by daily accrual with daily compounding:
            value = amount * (1 + (r - f) / 365) ** d
        `fee_deducted` is the difference between gross growth and net growth,
        i.e. the amount withheld from the investor before they are paid.
    """
    amount = Decimal(str(amount))
    r = product.annual_rate / Decimal('100')
    f = product.fee_percent / Decimal('100')
    days = product.tenure_days

    if product.product_type == InvestmentProduct.ProductType.TREASURY_BILL:
        maturity_value = amount * (1 + r * days / Decimal('365'))
        fee = amount * f
        net_payout = maturity_value - fee
        net_interest = net_payout - amount
        net_annualized_rate = (net_interest / amount) * Decimal('365') / days * Decimal('100')
        daily_rate = None
        open_ended = False
    elif product.product_type == InvestmentProduct.ProductType.MONEY_MARKET_FUND:
        net_annual = (r - f) * Decimal('100')
        maturity_value = amount
        fee = Decimal('0.00')
        net_payout = amount
        net_interest = Decimal('0.00')
        net_annualized_rate = net_annual
        daily_rate = net_annual / Decimal('365')
        open_ended = True
    else:
        gross_value = amount * (1 + r / Decimal('365')) ** days
        net_value = amount * (1 + (r - f) / Decimal('365')) ** days
        maturity_value = gross_value
        fee = gross_value - net_value
        net_payout = net_value
        net_interest = net_payout - amount
        net_annualized_rate = (net_interest / amount) * Decimal('365') / days * Decimal('100')
        daily_rate = (r - f) * Decimal('100') / Decimal('365')
        open_ended = False

    return {
        'amount': _money(amount),
        'maturity_value': _money(maturity_value),
        'fee_deducted': _money(fee),
        'net_payout': _money(net_payout),
        'net_interest': _money(net_interest),
        'net_annualized_rate': net_annualized_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'daily_rate': daily_rate.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        if daily_rate is not None else None,
        'open_ended': open_ended,
    }


def daily_interest_rate(product):
    """Net daily interest rate (fraction) for an investment product."""
    return (product.annual_rate - product.fee_percent) / Decimal('100') / Decimal('365')


def accrue_investment(inv, now=None):
    """Compute and deposit daily interest for open-ended (money market)
    investments. Interest is deposited into the investment wallet and a
    Transaction is recorded. Returns the amount deposited."""
    if inv.product.product_type != InvestmentProduct.ProductType.MONEY_MARKET_FUND:
        return Decimal('0')
    if inv.status != 'active':
        return Decimal('0')
    now = now or timezone.now()
    last = inv.last_accrual_date or inv.invested_at
    days = (now - last).days
    if days <= 0:
        return Decimal('0')
    value = inv.amount + inv.interest_accrued
    rate = daily_interest_rate(inv.product)
    accrued = _money(value * rate * days)
    if accrued <= 0:
        return Decimal('0')
    with transaction.atomic():
        inv.interest_accrued += accrued
        inv.last_accrual_date = now
        inv.save(update_fields=['interest_accrued', 'last_accrual_date'])
        if inv.wallet:
            inv.wallet.balance += accrued
            inv.wallet.save(update_fields=['balance'])
        Transaction.objects.create(
            user=inv.user,
            amount=accrued,
            category='interest',
            type='deposit',
            description=f'Daily interest on {inv.product.name} '
                        f'(wallet {inv.wallet.wallet_number if inv.wallet else "-"})',
            date=now,
        )
        InvestmentReturn.objects.create(
            user=inv.user,
            investment=inv,
            return_type=InvestmentReturn.ReturnType.DAILY_INTEREST,
            amount=accrued,
            description=f'Daily interest on {inv.product.name}',
        )
    return accrued


def accrue_user_investments(user, now=None):
    """Accrue daily interest for all of a user's active money market
    investments. Returns the total deposited."""
    total = Decimal('0')
    for inv in Investment.objects.filter(user=user, status='active').select_related('product'):
        total += accrue_investment(inv, now=now)
    return total


class InvestmentProduct(models.Model):
    class ProductType(models.TextChoices):
        TREASURY_BILL = 'treasury_bill', 'Treasury Bill'
        MONEY_MARKET_FUND = 'money_market_fund', 'Money Market Fund'
        BALANCED_UNIT_TRUST = 'balanced_unit_trust', 'Balanced Unit Trust'

    name = models.CharField(max_length=150)
    product_type = models.CharField(max_length=30, choices=ProductType.choices)
    tagline = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    annual_rate = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text='Gross annualized rate in % (e.g. latest T-bill auction rate).',
    )
    fee_percent = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal('0.000'),
        help_text='Deduction % taken before the investor is paid (service/management fee).',
    )
    tenure_days = models.PositiveIntegerField(
        default=91,
        help_text='Maturity / projection period in days.',
    )
    min_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    is_active = models.BooleanField(default=True)
    is_best_match = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_best_match', 'id']

    def __str__(self):
        return self.name

    def get_display_description(self):
        min_amount = int(self.min_amount)
        prefix = f'{self.tagline} · ' if self.tagline else ''
        return f'{prefix}Min KSh {min_amount:,}'

    def compute(self, amount):
        return compute_investment(amount, self)


class InvestmentWallet(models.Model):
    """Wallet holding invested money, one per user per product type.

    A wallet is created on the user's first investment in a product type and
    gets a system-generated, distinguishable 12-digit wallet_number (like the
    user's account_number). Money invested is moved from the user's account
    balance into this wallet, and back out at redemption.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investment_wallets',
    )
    product_type = models.CharField(max_length=30, choices=InvestmentProduct.ProductType.choices)
    wallet_number = models.CharField(max_length=12, unique=True, blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product_type')

    def save(self, *args, **kwargs):
        if not self.wallet_number:
            self.wallet_number = generate_wallet_number(self.product_type)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_product_type_display()} wallet {self.wallet_number} - {self.user.username}"


class InvestmentReturn(models.Model):
    """One return event on an investment: daily interest accrual, or the
    interest payout at maturity/redemption."""

    class ReturnType(models.TextChoices):
        DAILY_INTEREST = 'daily_interest', 'Daily Interest'
        REDEMPTION = 'redemption', 'Redemption'
        MATURITY = 'maturity', 'Maturity'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investment_returns',
    )
    investment = models.ForeignKey(
        'Investment',
        on_delete=models.CASCADE,
        related_name='returns',
    )
    return_type = models.CharField(max_length=20, choices=ReturnType.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.investment.product.name} return {self.amount} ({self.user.username})'


class Investment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='investments',
    )
    product = models.ForeignKey(
        InvestmentProduct,
        on_delete=models.PROTECT,
        related_name='investments',
    )
    wallet = models.ForeignKey(
        InvestmentWallet,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='investments',
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    maturity_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Gross payout before deduction.',
    )
    fee_deducted = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Amount deducted from the investor before payout.',
    )
    net_payout = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='What the investor actually receives at maturity.',
    )
    interest_accrued = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Interest earned so far (money market funds accrue daily).',
    )
    last_accrual_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time daily interest was deposited for this investment.',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    invested_at = models.DateTimeField(auto_now_add=True)
    maturity_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Maturity for fixed-term products; money market funds are open-ended.',
    )

    class Meta:
        ordering = ['-invested_at']

    def is_open_ended(self):
        return self.product.product_type == InvestmentProduct.ProductType.MONEY_MARKET_FUND

    def current_value(self):
        """Current value of this investment (principal + interest accrued)."""
        if self.is_open_ended():
            return self.amount + self.interest_accrued
        return self.net_payout

    def __str__(self):
        return f"{self.product.name} - {self.user.username} ({self.status})"
