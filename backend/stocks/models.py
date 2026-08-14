from decimal import Decimal
import random
import string

from django.conf import settings
from django.db import models


def generate_stock_wallet_number():
    """Unique 12-digit wallet number for the shares wallet (prefix '8')."""
    while True:
        number = '8' + ''.join(random.choices(string.digits, k=11))
        if not StockWallet.objects.filter(wallet_number=number).exists():
            return number


class Stock(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=150)
    sector = models.CharField(max_length=100, blank=True, default='')
    current_price = models.DecimalField(max_digits=12, decimal_places=2)
    previous_close = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    @property
    def change_percent(self):
        if self.previous_close and self.previous_close > 0:
            return ((self.current_price - self.previous_close)
                    / self.previous_close * Decimal('100'))
        return Decimal('0.00')

    def __str__(self):
        return f'{self.code} - {self.name}'


class StockWallet(models.Model):
    """One wallet per user that holds the cost basis of shares bought.

    Money spent buying shares moves from the user's account balance into this
    wallet; selling moves it back (the profit/loss is credited to the user)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_wallet',
    )
    wallet_number = models.CharField(max_length=12, unique=True, blank=True)
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Cost basis of the shares held in this wallet.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.wallet_number:
            self.wallet_number = generate_stock_wallet_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Stocks wallet {self.wallet_number} - {self.user.username}'


class ShareHolding(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='share_holdings',
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.PROTECT,
        related_name='holdings',
    )
    wallet = models.ForeignKey(
        StockWallet,
        on_delete=models.PROTECT,
        related_name='holdings',
    )
    quantity = models.PositiveIntegerField()
    avg_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'stock')
        ordering = ['stock__code']

    @property
    def cost_basis(self):
        return self.avg_price * self.quantity

    @property
    def current_value(self):
        return self.stock.current_price * self.quantity

    @property
    def pnl(self):
        return self.current_value - self.cost_basis

    def __str__(self):
        return f'{self.stock.code} x{self.quantity} - {self.user.username}'


class CompanyRevenue(models.Model):
    """Each charge collected by AlexiaFinancials on share trades.

    Every broker fee and government tax deducted on a buy or sell is recorded
    here as a gain for the company, so the running revenue can be audited and
    aggregated per source. Each row is tied to the user's stock account number
    and the trade transaction that produced it."""
    company = models.CharField(max_length=100, default='AlexiaFinancials')
    source = models.CharField(max_length=50)  # 'broker_fee' | 'government_tax'
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    charge_type = models.CharField(
        max_length=40, default='stocks',
        help_text="What kind of transaction produced this charge "
                  "(e.g. 'transfer', 'withdrawal', 'goal_funding', "
                  "'chama_contribution', 'chama_join', 'stocks').",
    )
    charge_rate = models.DecimalField(
        max_digits=6, decimal_places=3, default=Decimal('0.000'),
        help_text="Percentage rate that produced this charge (e.g. 2.000).",
    )
    trade_type = models.CharField(max_length=10)  # 'buy' | 'sell' | 'debit' | 'credit'
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_charges',
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='charges',
    )
    account_number = models.CharField(
        max_length=12,
        help_text="The user's shares wallet number that was charged.",
    )
    transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_charges',
        help_text='The trade transaction this charge belongs to.',
    )
    # Company ledger columns
    total_collected = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Gross amount collected from the investor in this trade "
                  "(buy: total cost incl. charges; sell: gross proceeds).",
    )
    outflow = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Any cash paid out by the company on this entry "
                  "(e.g. dividends/payouts). 0 for a charge.",
    )
    investor_balances_total = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Snapshot of the total balances across all investor "
                  "share wallets at the time of the charge.",
    )
    user_deposit_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Snapshot of the trading user's main account balance "
                  "at the time of the charge.",
    )
    app_total_charges = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Running total of all transaction charges collected by the "
                  "company across every user so far (including this charge).",
    )
    total_invested_goals = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Total money all users have saved toward goals.",
    )
    total_invested_chamas = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Total money all members have contributed to chamas.",
    )
    total_invested_stocks = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text="Total cost-basis of all shares held across every investor.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company} · {self.source} KSh {self.amount} ({self.trade_type}) · {self.account_number}'
