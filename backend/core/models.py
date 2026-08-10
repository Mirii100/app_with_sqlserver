from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    phone_number = models.CharField(max_length=20, unique=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    county = models.CharField(max_length=100, null=True, blank=True)
    town = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    employment_type = models.CharField(max_length=50, null=True, blank=True)
    monthly_income = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    loan_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    loan_used = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)

    # New image fields
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    id_photo = models.ImageField(upload_to='id_photos/', null=True, blank=True)
    selfie_photo = models.ImageField(upload_to='selfies/', null=True, blank=True)

    def __str__(self):
        return self.username

class SecuritySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_settings')
    pin_hash = models.CharField(max_length=255, null=True, blank=True)
    biometric_enabled = models.BooleanField(default=False)
    last_pin_changed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Security settings for {self.user.username}"
