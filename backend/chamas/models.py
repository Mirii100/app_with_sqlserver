from django.db import models
from django.conf import settings

class Chama(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='administered_chamas')
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_contribution = models.DecimalField(max_digits=15, decimal_places=2)
    contribution_frequency = models.CharField(max_length=20, default='weekly')
    total_pool_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    member_count = models.IntegerField(default=1)
    invite_code = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ChamaMembership(models.Model):
    chama = models.ForeignKey(Chama, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chama_memberships')
    role = models.CharField(max_length=20, default='member')
    contributed_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, help_text="Total amount this member has contributed to the chama pool")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('chama', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.chama.name}"
