from django.db import models
from django.conf import settings
import json
import random
import string

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
