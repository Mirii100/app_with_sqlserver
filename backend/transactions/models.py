from django.db import models
from django.conf import settings
import json
import random
import string
from decimal import Decimal

_REFERENCE_CHARS = string.ascii_uppercase + string.digits


def _generate_reference():
    """Generate an uppercase alphanumeric reference of length 10-12."""
    return ''.join(random.choices(_REFERENCE_CHARS, k=random.randint(10, 12)))

class BillerCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, help_text="Icon identifier for the UI")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SavingsGoal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='savings_goals')
    title = models.CharField(max_length=100)
    purpose = models.TextField(blank=True)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    saved_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    auto_save_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    auto_save_enabled = models.BooleanField(default=False)
    currency = models.CharField(max_length=10, default='KSh')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
    month = models.CharField(max_length=20)
    categories = models.TextField(default='{}', blank=True, help_text="JSON string of category spending")
    budget_limits = models.TextField(default='{}', blank=True, help_text="JSON string of budget limits per category")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'month')

    def get_categories(self):
        try:
            return json.loads(self.categories) if self.categories else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_categories(self, value):
        self.categories = json.dumps(value) if value else '{}'

    def get_budget_limits(self):
        try:
            return json.loads(self.budget_limits) if self.budget_limits else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_budget_limits(self, value):
        self.budget_limits = json.dumps(value) if value else '{}'

    def __str__(self):
        return f"Budget for {self.user.username} - {self.month}"

class UserLoanLimit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loan_limits')
    limit = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    used = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Loan limit for {self.user.username}: {self.limit} (used: {self.used})"

class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    broker_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    government_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    category = models.CharField(max_length=50)
    type = models.CharField(max_length=20) # 'deposit', 'withdrawal', etc.
    description = models.TextField(blank=True)
    reference = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        help_text="System-generated transaction reference code (10-12 uppercase alphanumeric characters)",
    )
    date = models.DateTimeField()
    timestamp = models.DateTimeField(auto_now_add=True)
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='repayments',
        help_text="Loan this transaction relates to (for repayments).",
    )
    is_partial = models.BooleanField(
        default=False,
        help_text="True when a loan repayment only covers part of the outstanding balance.",
    )

    def _generate_unique_reference(self):
        while True:
            ref = _generate_reference()
            if not Transaction.objects.filter(reference=ref).exists():
                return ref

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_unique_reference()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.type} - {self.amount} by {self.user.username}"

class GoalTransaction(models.Model):
    savings_goal = models.ForeignKey(SavingsGoal, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goal_transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    type = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    reference = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        help_text="System-generated transaction reference code (10-12 uppercase alphanumeric characters)",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def _generate_unique_reference(self):
        while True:
            ref = _generate_reference()
            if not GoalTransaction.objects.filter(reference=ref).exists():
                return ref

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_unique_reference()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.type} - {self.amount} for {self.savings_goal.title}"


# --- Cheque services --------------------------------------------------------

CHEQUE_BOOK_FEE = Decimal('500.00')
CHEQUE_COURIER_FEE = Decimal('300.00')
STOP_PAYMENT_FEE = Decimal('250.00')


class ChequeBookRequest(models.Model):
    class DeliveryMethod(models.TextChoices):
        BRANCH = 'branch', 'Branch pickup'
        COURIER = 'courier', 'Courier delivery'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready for pickup'
        DISPATCHED = 'dispatched', 'Dispatched'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='cheque_book_requests')
    leaves = models.PositiveIntegerField(default=50)
    delivery_method = models.CharField(max_length=10, choices=DeliveryMethod.choices,
                                       default=DeliveryMethod.BRANCH)
    delivery_address = models.CharField(max_length=255, blank=True, default='')
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=CHEQUE_BOOK_FEE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=12, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _generate_unique_reference(self):
        while True:
            ref = _generate_reference()
            if not ChequeBookRequest.objects.filter(reference=ref).exists():
                return ref

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_unique_reference()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cheque book {self.leaves} leaves · {self.user.username} ({self.reference})"


class StopPaymentOrder(models.Model):
    class Reason(models.TextChoices):
        LOST = 'lost', 'Lost'
        STOLEN = 'stolen', 'Stolen'
        DAMAGED = 'damaged', 'Damaged'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='stop_payment_orders')
    cheque_from = models.CharField(max_length=20)
    cheque_to = models.CharField(max_length=20, blank=True, default='')
    reason = models.CharField(max_length=10, choices=Reason.choices, default=Reason.LOST)
    date_issued = models.DateField(null=True, blank=True)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=STOP_PAYMENT_FEE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    reference = models.CharField(max_length=12, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _generate_unique_reference(self):
        while True:
            ref = _generate_reference()
            if not StopPaymentOrder.objects.filter(reference=ref).exists():
                return ref

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_unique_reference()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Stop {self.cheque_from}-{self.cheque_to or self.cheque_from} · {self.user.username}"


# --- Foreign exchange -------------------------------------------------------

FX_FEE = Decimal('50.00')


class FxRate(models.Model):
    """Exchange rate against KES: 1 unit of ``code`` = ``rate`` KES."""
    code = models.CharField(max_length=3, unique=True)
    rate = models.DecimalField(max_digits=12, decimal_places=4)
    previous_rate = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def direction(self):
        if self.previous_rate is None or self.rate == self.previous_rate:
            return 'flat'
        return 'up' if self.rate > self.previous_rate else 'down'

    def __str__(self):
        return f"1 {self.code} = {self.rate} KES"


class CurrencyWallet(models.Model):
    """Per-user foreign currency wallet (e.g. USD/EUR/GBP balances)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='currency_wallets')
    code = models.CharField(max_length=3)
    balance = models.DecimalField(max_digits=18, decimal_places=4, default=0.0)

    class Meta:
        unique_together = ('user', 'code')

    def __str__(self):
        return f"{self.user.username} · {self.balance} {self.code}"


# --- Crypto trading ---------------------------------------------------------

CRYPTO_TRADE_FEE_RATE = Decimal('0.005')  # 0.5%


class CryptoAsset(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    glyph = models.CharField(max_length=4, blank=True, default='')
    color_hex = models.CharField(max_length=9, blank=True, default='')
    price_kes = models.DecimalField(max_digits=18, decimal_places=2)
    previous_price_kes = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def change_pct(self):
        if not self.previous_price_kes or self.previous_price_kes == 0:
            return Decimal('0')
        return ((self.price_kes - self.previous_price_kes) / self.previous_price_kes) * 100

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class CryptoHolding(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='crypto_holdings')
    asset = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE,
                              related_name='holdings')
    quantity = models.DecimalField(max_digits=24, decimal_places=8, default=0.0)

    class Meta:
        unique_together = ('user', 'asset')

    def __str__(self):
        return f"{self.user.username}: {self.quantity} {self.asset.symbol}"


# --- Digital cheques --------------------------------------------------------

class Cheque(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CLEARED = 'cleared', 'Cleared'
        BOUNCED = 'bounced', 'Bounced'
        CANCELLED = 'cancelled', 'Cancelled'
        STOPPED = 'stopped', 'Stopped'

    issuer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='cheques_issued')
    payee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='cheques_received')
    cheque_number = models.CharField(max_length=10, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    memo = models.CharField(max_length=140, blank=True, default='')
    due_date = models.DateField(null=True, blank=True,
                                help_text='Post-dated cheques cannot be cleared before this date.')
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING)
    status_note = models.CharField(max_length=255, blank=True, default='')
    reference = models.CharField(max_length=12, unique=True, null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def _generate_unique_number():
        while True:
            number = ''.join(random.choices(string.digits, k=6))
            if not Cheque.objects.filter(cheque_number=number).exists():
                return number

    def _generate_unique_reference(self):
        while True:
            ref = _generate_reference()
            if not Cheque.objects.filter(reference=ref).exists():
                return ref

    def save(self, *args, **kwargs):
        if not self.cheque_number:
            self.cheque_number = self._generate_unique_number()
        if not self.reference:
            self.reference = self._generate_unique_reference()
        super().save(*args, **kwargs)

    def is_stop_payment_active(self):
        """True when an active stop-payment order covers this cheque number."""
        num = self.cheque_number.zfill(20)
        orders = StopPaymentOrder.objects.filter(
            user=self.issuer, status=StopPaymentOrder.Status.ACTIVE)
        for order in orders:
            start = order.cheque_from.zfill(20)
            end = (order.cheque_to or order.cheque_from).zfill(20)
            if start <= num <= end:
                return True
        return False

    def __str__(self):
        return f"Cheque {self.cheque_number} · {self.amount} KES · " \
               f"{self.issuer.username} → {self.payee.username} ({self.status})"
