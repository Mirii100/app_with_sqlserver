from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class LoanProduct(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_products',
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')

    is_best_match = models.BooleanField(default=False)
    is_outline = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loans',
    )

    loan_product = models.ForeignKey(
        LoanProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loans',
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
    )

    approved_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
    )

    outstanding_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
    )

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
    )

    duration_months = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )

    purpose = models.CharField(
        max_length=255,
        blank=True,
        default='',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Loan #{self.id} - {self.user.username}"