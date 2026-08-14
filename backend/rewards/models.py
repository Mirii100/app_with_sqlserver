from django.conf import settings
from django.db import models


class Reward(models.Model):
    """A reward a user can redeem with their points balance."""

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    points_cost = models.PositiveIntegerField()
    icon = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text='Optional emoji shown in the app, e.g. 📱',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['points_cost']

    def __str__(self):
        return f'{self.name} ({self.points_cost} pts)'


class RewardTransaction(models.Model):
    class Status(models.TextChoices):
        REDEEMED = 'redeemed', 'Redeemed'
        FULFILLED = 'fulfilled', 'Fulfilled'
        CANCELLED = 'cancelled', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reward_transactions',
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.PROTECT,
        related_name='transactions',
    )
    points_cost = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REDEEMED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} redeemed {self.reward.name}'
