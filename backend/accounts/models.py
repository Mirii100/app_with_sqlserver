from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
import random
import string


def generate_biller_account_number():
    """Generate a unique 12-digit account number for a paybiller.

    Biller accounts start with '4' so they are distinguishable from
    user accounts and investment wallets (which use 5/6/7).
    """
    while True:
        number = '4' + ''.join(random.choices(string.digits, k=11))
        if not Biller.objects.filter(account_number=number).exists():
            return number

class Account(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='account')
    account_number = models.CharField(max_length=50, unique=True)
    account_type = models.CharField(max_length=50, default='savings')
    currency = models.CharField(max_length=10, default='KSh')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    available_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.account_type} - {self.account_number}"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_account(sender, instance, created, **kwargs):
    if created:
        Account.objects.get_or_create(
            user=instance,
            defaults={
                'account_number': instance.account_number,
                'account_type': 'savings',
                'currency': 'KSh',
                'balance': 0.0,
                'available_balance': 0.0,
                'status': 'active',
            }
        )

class Biller(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='billers')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, default='')
    account_number = models.CharField(max_length=50, blank=True, unique=True, default='',
                                      help_text="System-generated unique account number for this biller")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0,
                                  help_text="Amount paid to this biller's account")
    icon = models.CharField(max_length=50, blank=True, default='')
    title = models.CharField(max_length=100, blank=True, default='', help_text="Display title for the biller")
    subtitle = models.CharField(max_length=200, blank=True, default='', help_text="Subtitle/secondary text for the biller")

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = generate_biller_account_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Beneficiary(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='beneficiaries')
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, help_text="Recipient phone number")
    account_number = models.CharField(max_length=50, blank=True, default='')
    bank_name = models.CharField(max_length=100, blank=True, default='', help_text="Bank name for bank beneficiaries")
    is_bank = models.BooleanField(default=False, help_text="True for bank transfers, False for mobile money")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'phone_number')

    def __str__(self):
        return self.name
