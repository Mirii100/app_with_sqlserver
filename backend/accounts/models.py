from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
import random
import string
from datetime import datetime, timedelta


def generate_biller_account_number():
    """Generate a unique 12-digit account number for a paybiller.

    Biller accounts start with '4' so they are distinguishable from
    user accounts and investment wallets (which use 5/6/7).
    """
    while True:
        number = '4' + ''.join(random.choices(string.digits, k=11))
        if not Biller.objects.filter(account_number=number).exists():
            return number


def generate_cvv():
    """Generate a random 3-digit CVV."""
    while True:
        cvv = ''.join(random.choices(string.digits, k=3))
        return cvv


def generate_card_number():
    """Generate a virtual card number starting with 5312 (virtual card prefix)."""
    while True:
        number = '5312' + ''.join(random.choices(string.digits, k=12))
        # Check if this card number already exists
        if not CreditCard.objects.filter(card_number=number).exists() and \
           not DebitCard.objects.filter(card_number=number).exists():
            return number


def luhn_check(card_number):
    """Simple Luhn check for card number validation."""
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0


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

    @property
    def card_count(self):
        """Return total number of cards for this user."""
        return CreditCard.objects.filter(user=self.user, is_active=True).count() + \
               DebitCard.objects.filter(user=self.user, is_active=True).count()


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


class CreditCard(models.Model):
    """Virtual credit card for the user."""
    
    class CardType(models.TextChoices):
        VISA = 'visa', 'Visa'
        MASTERCARD = 'mastercard', 'MasterCard'
        AMEX = 'amex', 'American Express'
        VIRTUAL = 'virtual', 'Virtual'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        ACTIVE = 'active', 'Active'
        FROZEN = 'frozen', 'Frozen'
        EXPIRED = 'expired', 'Expired'
        BLOCKED = 'blocked', 'Blocked'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_cards')
    account_number = models.CharField(max_length=50, blank=True, help_text="User's bank account number this card is linked to")
    card_number = models.CharField(max_length=16, unique=True, blank=True, help_text="Full card number (auto-generated, masked on display)")
    card_type = models.CharField(max_length=20, choices=CardType.choices, default=CardType.VISA)
    cardholder_name = models.CharField(max_length=100)
    reason_for_applying = models.CharField(max_length=200, blank=True, help_text="Reason why the card is being applied for")
    expiry_date = models.CharField(max_length=5, help_text="Format: MM/YY")
    cvv = models.CharField(max_length=3, help_text="System-generated CVV")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    spend_limit = models.DecimalField(max_digits=12, decimal_places=2, default=100000.00, help_text="Daily spend limit in KSh")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Credit Card"
        verbose_name_plural = "Credit Cards"
        ordering = ['-created_at']
    
    def __str__(self):
        """Display masked card number: 5312 •••• •••• •••• 8841"""
        if len(self.card_number) >= 16:
            masked = f"{self.card_number[:4]} •••• •••• •••• {self.card_number[-4:]}"
        else:
            masked = "INVALID"
        return f"{masked} ({self.cardholder_name})"
    
    def save(self, *args, **kwargs):
        if not self.card_number:
            self.card_number = generate_card_number()
        if not self.account_number:
            self.account_number = getattr(self.user, 'account_number', '') or ''
        super().save(*args, **kwargs)
    
    @property
    def last_four(self):
        """Return last 4 digits of card number."""
        if len(self.card_number) >= 4:
            return self.card_number[-4:]
        return "0000"
    
    @property
    def first_four(self):
        """Return first 4 digits of card number."""
        if len(self.card_number) >= 4:
            return self.card_number[:4]
        return "0000"
    
    def is_expired(self):
        """Check if card is expired based on expiry_date (MM/YY)."""
        from datetime import datetime
        try:
            exp_month, exp_year = self.expiry_date.split('/')
            exp_date = datetime(2000 + int(exp_year), int(exp_month), 1)
            return datetime.now() > exp_date
        except (ValueError, IndexError):
            return True
    
    @property
    def balance(self):
        """Return the user's account balance."""
        return self.user.account.balance
    
    @property
    def available_balance(self):
        """Return the user's available account balance."""
        return self.user.account.available_balance

    def mask_card_number(self):
        """Return masked card number for display."""
        if len(self.card_number) >= 16:
            return f"{self.card_number[:4]} •••• •••• •••• {self.card_number[-4:]}"
        return "INVALID"


class DebitCard(models.Model):
    """Virtual debit card for the user."""
    
    class CardType(models.TextChoices):
        VISA = 'visa', 'Visa'
        MASTERCARD = 'mastercard', 'MasterCard'
        AMEX = 'amex', 'American Express'
        VIRTUAL = 'virtual', 'Virtual'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        ACTIVE = 'active', 'Active'
        FROZEN = 'frozen', 'Frozen'
        EXPIRED = 'expired', 'Expired'
        BLOCKED = 'blocked', 'Blocked'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='debit_cards')
    account_number = models.CharField(max_length=50, blank=True, help_text="User's bank account number this card is linked to")
    card_number = models.CharField(max_length=16, unique=True, blank=True, help_text="Full card number (auto-generated, masked on display)")
    card_type = models.CharField(max_length=20, choices=CardType.choices, default=CardType.VIRTUAL)
    cardholder_name = models.CharField(max_length=100)
    reason_for_applying = models.CharField(max_length=200, blank=True, help_text="Reason why the card is being applied for")
    expiry_date = models.CharField(max_length=5, help_text="Format: MM/YY")
    cvv = models.CharField(max_length=3, help_text="System-generated CVV")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    spend_limit = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00, help_text="Daily spend limit in KSh")
    is_contactless = models.BooleanField(default=True, help_text="Enable/contactless payments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Debit Card"
        verbose_name_plural = "Debit Cards"
        ordering = ['-created_at']
    
    def __str__(self):
        """Display masked card number: 5312 •••• •••• •••• 8841"""
        if len(self.card_number) >= 16:
            masked = f"{self.card_number[:4]} •••• •••• •••• {self.card_number[-4:]}"
        else:
            masked = "INVALID"
        return f"{masked} ({self.cardholder_name})"
    
    def save(self, *args, **kwargs):
        if not self.card_number:
            self.card_number = generate_card_number()
        if not self.account_number:
            self.account_number = getattr(self.user, 'account_number', '') or ''
        super().save(*args, **kwargs)
    
    @property
    def last_four(self):
        """Return last 4 digits of card number."""
        if len(self.card_number) >= 4:
            return self.card_number[-4:]
        return "0000"
    
    @property
    def first_four(self):
        """Return first 4 digits of card number."""
        if len(self.card_number) >= 4:
            return self.card_number[:4]
        return "0000"
    
    def is_expired(self):
        """Check if card is expired based on expiry_date (MM/YY)."""
        from datetime import datetime
        try:
            exp_month, exp_year = self.expiry_date.split('/')
            exp_date = datetime(2000 + int(exp_year), int(exp_month), 1)
            return datetime.now() > exp_date
        except (ValueError, IndexError):
            return True
    
    @property
    def balance(self):
        """Return the user's account balance."""
        return self.user.account.balance
    
    @property
    def available_balance(self):
        """Return the user's available account balance."""
        return self.user.account.available_balance

    def mask_card_number(self):
        """Return masked card number for display."""
        if len(self.card_number) >= 16:
            return f"{self.card_number[:4]} •••• •••• •••• {self.card_number[-4:]}"
        return "INVALID"


class UserCardSettings(models.Model):
    """User-level card settings and preferences."""
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='card_settings')
    
    # Default card for purchases
    default_credit_card = models.ForeignKey(
        CreditCard, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='default_for_user'
    )
    default_debit_card = models.ForeignKey(
        DebitCard, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='default_for_user'
    )
    
    # Global settings
    online_payments_enabled = models.BooleanField(default=True, help_text="Enable online card payments")
    contactless_enabled = models.BooleanField(default=True, help_text="Enable contactless payments")
    sms_notifications = models.BooleanField(default=True, help_text="SMS transaction notifications")
    email_notifications = models.BooleanField(default=True, help_text="Email transaction notifications")
    
    # Daily limits across all cards
    total_daily_spend_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=150000.00,
        help_text="Total daily spend limit across all cards in KSh"
    )
    
    # Notification preferences
    low_spend_alert = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=10000.00,
        help_text="Spend alert threshold in KSh"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Card Settings"
        verbose_name_plural = "User Card Settings"
    
    def __str__(self):
        return f"Card settings for {self.user.email}"
    
    @property
    def active_credit_cards(self):
        """Return active credit cards."""
        return CreditCard.objects.filter(user=self.user, status=CreditCard.Status.ACTIVE)
    
    @property
    def active_debit_cards(self):
        """Return active debit cards."""
        return DebitCard.objects.filter(user=self.user, status=DebitCard.Status.ACTIVE)


@receiver(post_save, sender=CreditCard)
def fund_credit_card(sender, instance, created, **kwargs):
    """Deduct spend_limit from user account when credit card is created."""
    if created:
        user_account = instance.user.account
        if user_account.balance >= instance.spend_limit:
            user_account.balance -= instance.spend_limit
            user_account.save(update_fields=['balance'])
            # Create transaction record
            from backend.transactions.models import Transaction
            Transaction.objects.create(
                user=instance.user,
                amount=instance.spend_limit,
                broker_fee=0.00,
                government_tax=0.00,
                category='card_creation',
                type='withdrawal',
                description=f'Credit card funding - {instance.card_type}'
            )


@receiver(post_save, sender=DebitCard)
def fund_debit_card(sender, instance, created, **kwargs):
    """Deduct spend_limit from user account when debit card is created."""
    if created:
        user_account = instance.user.account
        if user_account.balance >= instance.spend_limit:
            user_account.balance -= instance.spend_limit
            user_account.save(update_fields=['balance'])
            # Create transaction record
            from backend.transactions.models import Transaction
            Transaction.objects.create(
                user=instance.user,
                amount=instance.spend_limit,
                broker_fee=0.00,
                government_tax=0.00,
                category='card_creation',
                type='withdrawal',
                description=f'Debit card funding - {instance.card_type}'
            )