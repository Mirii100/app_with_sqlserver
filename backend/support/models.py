import random
import string

from django.conf import settings
from django.db import models


def generate_ticket_reference():
    """Unique human-friendly ticket reference, e.g. TKT-483920."""
    while True:
        ref = 'TKT-' + ''.join(random.choices(string.digits, k=6))
        if not SupportTicket.objects.filter(reference=ref).exists():
            return ref


class SupportTicket(models.Model):
    class Category(models.TextChoices):
        TRANSACTION = 'transaction', 'Transaction'
        ACCOUNT = 'account', 'Account'
        LOAN = 'loan', 'Loan'
        INVESTMENT = 'investment', 'Investment'
        STOCKS = 'stocks', 'Stocks'
        TECHNICAL = 'technical', 'Technical'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
    )
    reference = models.CharField(max_length=20, unique=True, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    resolution_note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_ticket_reference()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.reference} - {self.subject} ({self.user.username})'
