from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import string
import random

def generate_account_number():
    """Generate a unique 12-digit account number."""
    while True:
        number = ''.join(random.choices(string.digits, k=12))
        # Ensure it starts with a non-zero digit
        if number[0] != '0':
            return number

def generate_referral_code():
    """Generate a unique 8-character referral code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=8))
        if not User.objects.filter(referral_code=code).exists():
            return code

class AnalyticsDashboard(models.Model):
    class Meta:
        verbose_name = 'Business Analytics'
        verbose_name_plural = 'Business Analytics'
    name = models.CharField(max_length=1, default='A')
    
    def __str__(self):
        return 'Business Analytics'

class User(AbstractUser):
    phone_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    county = models.CharField(max_length=100, null=True, blank=True)
    town = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    employment_type = models.CharField(max_length=50, null=True, blank=True)
    monthly_income = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    loan_wallet_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    chama_wallet_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    goal_wallet_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    loan_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    loan_used = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    points = models.PositiveIntegerField(default=0, help_text="Loyalty points balance used to redeem rewards.")
    
    # Unique account number for the user
    account_number = models.CharField(max_length=12, unique=True, blank=True, help_text="Unique account number generated on user creation")

    # Referral
    referral_code = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        help_text="Unique referral code shared with friends to earn points.",
    )
    referred_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referrals',
        help_text="User who referred this account.",
    )

    # New image fields
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    id_photo = models.ImageField(upload_to='id_photos/', null=True, blank=True)
    selfie_photo = models.ImageField(upload_to='selfies/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = generate_account_number()
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

def generate_payment_qr_token():
    """Generate a unique KESHPAY token embedded in the user's payment QR."""
    while True:
        token = 'KESHPAY-' + ''.join(random.choices(string.digits + string.ascii_uppercase, k=8))
        if not PaymentQrCode.objects.filter(token=token).exists():
            return token


class PaymentQrCode(models.Model):
    """Canonical, scannable payment QR payload for a user.

    The QR encodes this record's ``payload`` (JSON with the owner's
    account number, email, phone number, national ID and name) plus a
    unique ``token`` that other users can scan to pay them. Stored in
    the database so scanned tokens can be resolved server-side.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='payment_qr',
    )
    token = models.CharField(max_length=24, unique=True)
    payload = models.TextField(help_text="JSON string encoded inside the QR image")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = generate_payment_qr_token()
        super().save(*args, **kwargs)

    def build_payload(self):
        """Compose the QR JSON from the latest identity data."""
        import json
        return json.dumps({
            'v': 1,
            'type': 'KESHPAY',
            'token': self.token,
            'userId': str(self.user_id),
            'name': self.user.full_name or self.user.username,
            'account': self.user.account_number,
            'email': self.user.email,
            'phone': self.user.phone_number,
            'nationalId': self.user.national_id or '',
        })

    def refresh_payload(self):
        self.payload = self.build_payload()
        self.save(update_fields=['payload', 'updated_at'])

    def __str__(self):
        return f"Payment QR for {self.user.username} ({self.token})"


class SecuritySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_settings')
    pin_hash = models.CharField(max_length=255, null=True, blank=True)
    biometric_enabled = models.BooleanField(default=False)
    last_pin_changed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Security settings for {self.user.username}"


class OtpCode(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
    ]
    PURPOSE_CHOICES = [
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code_hash = models.CharField(max_length=255)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='login')
    destination = models.CharField(max_length=255, blank=True, default='', help_text="Contact the code was sent to")
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0, help_text="Number of failed verification attempts")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def is_valid_code(self, code):
        from django.contrib.auth.hashers import check_password
        return check_password(str(code), self.code_hash)

    def __str__(self):
        return f"OTP for {self.user.username} ({self.get_channel_display()})"
