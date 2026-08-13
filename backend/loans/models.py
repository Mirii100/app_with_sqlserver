from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import F
from django.utils import timezone


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


@receiver(pre_save, sender=Loan)
def capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Loan.objects.get(pk=instance.pk).status
        except Loan.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Loan)
def release_funds_on_approval(sender, instance, created, **kwargs):
    """When a loan transitions to 'approved' or 'active', release funds to the user's account."""
    old_status = getattr(instance, '_old_status', None)

    if created:
        return

    was_inactive = old_status not in ['approved', 'active']
    is_now_active = instance.status in ['approved', 'active']

    if not (was_inactive and is_now_active):
        return

    amount = instance.approved_amount if instance.approved_amount and instance.approved_amount > 0 else instance.amount

    if amount and amount > 0:
        User = type(instance.user)

        # Update the user's loan wallet and loan used fields
        User.objects.filter(id=instance.user.id).update(
            loan_wallet_balance=F('loan_wallet_balance') + amount,
            loan_used=F('loan_used') + amount
        )

        if not instance.outstanding_amount or instance.outstanding_amount == 0:
            Loan.objects.filter(id=instance.id).update(outstanding_amount=amount)

        from transactions.models import Transaction
        Transaction.objects.create(
            user=instance.user,
            amount=amount,
            category='loan_disbursement',
            type='deposit',
            description=f'Loan #{instance.id} disbursed to Loan Wallet',
            date=timezone.now(),
        )