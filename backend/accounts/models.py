from django.db import models
from django.conf import settings

class Account(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=50, unique=True)
    account_type = models.CharField(max_length=50)
    currency = models.CharField(max_length=10, default='KSh')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    available_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.account_type} - {self.account_number}"

class Biller(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='billers')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    account_number = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name
