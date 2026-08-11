from django.db import models
from django.conf import settings


class UserDevice(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices',
    )
    device_fingerprint = models.CharField(max_length=255)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'device_fingerprint')

    def __str__(self):
        return f"{self.user.username} - {self.device_fingerprint[:32]}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_device_login', 'New Device Login'),
        ('budget_alert', 'Budget Alert'),
        ('payment_received', 'Payment Received'),
        ('loan_update', 'Loan Update'),
        ('security_alert', 'Security Alert'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    is_read = models.BooleanField(default=False)
    extra_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()} - {self.title} ({self.user.username})"
