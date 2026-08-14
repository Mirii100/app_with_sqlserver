from django.conf import settings
from django.db import models


class FinancialAdvice(models.Model):
    class AdviceType(models.TextChoices):
        SAVINGS = 'savings', 'Savings'
        SPENDING = 'spending', 'Spending'
        DEBT = 'debt', 'Debt'
        INVESTMENT = 'investment', 'Investment'
        ALERT = 'alert', 'Alert'
        GENERAL = 'general', 'General'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='financial_advice',
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    advice_type = models.CharField(max_length=20, choices=AdviceType.choices)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.user.username})'
