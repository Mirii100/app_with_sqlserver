"""Loyalty points: configurable award values and a single, idempotent
grant function used by every feature that earns points.

Each award is recorded in PointsAward with a unique `key` (e.g. the
transaction reference or investment id) so the same event can never be
rewarded twice.
"""

from django.db import transaction
from django.db.models import F

# Flat points granted per event. Adjust here to change the scheme.
SIGNUP_POINTS = 25
REFERRAL_POINTS = 50
DEPOSIT_POINTS = 10
INVESTMENT_POINTS = 20
GOAL_SAVINGS_POINTS = 5

DEFAULT_POINTS = {
    'signup': SIGNUP_POINTS,
    'referral': REFERRAL_POINTS,
    'deposit': DEPOSIT_POINTS,
    'investment': INVESTMENT_POINTS,
    'goal_saving': GOAL_SAVINGS_POINTS,
}


def award_points(user, reason, key, points=None, description=None, notify=True):
    """Grant `points` (default depends on `reason`) for `key`, once only.

    Returns (awarded, points): `awarded` is True only when the points were
    actually granted (first time the key is seen). A Notification is created
    for the user unless `notify` is False.
    """
    from .models import PointsAward
    from notifications.models import Notification

    if points is None:
        points = DEFAULT_POINTS[reason]

    with transaction.atomic():
        award, created = PointsAward.objects.get_or_create(
            key=key,
            defaults={
                'user': user,
                'reason': reason,
                'points': points,
                'description': description or '',
            },
        )
        if created:
            from django.contrib.auth import get_user_model
            get_user_model().objects.filter(id=user.id).update(points=F('points') + points)
            if notify:
                try:
                    Notification.objects.create(
                        user=user,
                        title=f'{points} points earned',
                        message=f'{description or "Activity reward"} — you earned {points} loyalty points.',
                        type='points',
                    )
                except Exception:
                    pass
    return created, points
