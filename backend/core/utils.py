"""Shared utilities for profile-completion reminders.

The functions here are used both by the ``notify_incomplete_profiles``
management command and by the Django admin action of the same name.
"""

import logging
from collections import namedtuple

from django.conf import settings
from django.core.mail import send_mail

from notifications.models import Notification

logger = logging.getLogger(__name__)

# Fields to check – (model_attribute, human-friendly label for email body)
REQUIRED_PROFILE_FIELDS = [
    ('phone_number', 'Phone Number'),
    ('national_id', 'National ID / Passport'),
    ('full_name', 'Full Name'),
    ('county', 'County'),
    ('town', 'Town / City'),
    ('employment_type', 'Employment Type'),
]

ProfileCheckResult = namedtuple('ProfileCheckResult', ['user', 'missing_labels'])


def find_users_with_incomplete_profiles(users):
    """Return a list of :class:`ProfileCheckResult` for *users* that are
    missing at least one required profile field."""
    results = []
    for user in users:
        missing_labels = []
        for attr, label in REQUIRED_PROFILE_FIELDS:
            value = getattr(user, attr, None)
            if value is None or str(value).strip() == '':
                missing_labels.append(label)
        if missing_labels:
            results.append(ProfileCheckResult(user=user, missing_labels=missing_labels))
    return results


def notify_user_incomplete_profile(user, missing_labels, dry_run=False):
    """Send an email (and in-app notification) to *user* listing the
    profile fields that still need to be filled in.

    Returns ``True`` when the notification was actually sent (not in
    dry-run mode) or would have been sent in dry-run mode.
    """
    if not user.email:
        logger.warning(
            'Cannot notify user %s: no email address', user.pk
        )
        return False

    field_list = '\n'.join(f'  - {label}' for label in missing_labels)

    subject = 'Action Required: Complete Your Alexia Profile'
    message = (
        f'Dear {user.get_full_name() or user.username},\n\n'
        f'We noticed that your Alexia profile is missing some '
        f'information. To unlock the full range of features and '
        f'ensure smooth transactions, please update the following '
        f'fields in your profile:\n\n'
        f'{field_list}\n\n'
        f'You can update these details in the Alexia app under '
        f'Profile > Personal details, or on the web at '
        f'your profile settings.\n\n'
        f'Thank you,\n— Alexia Financials Team'
    )

    if dry_run:
        logger.info(
            '[DRY RUN] Would email %s – missing: %s',
            user.email,
            ', '.join(missing_labels),
        )
    else:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            Notification.objects.create(
                user=user,
                title='Complete Your Profile',
                message=(
                    'Please update your profile with the following '
                    f'missing information: {", ".join(missing_labels)}.'
                ),
                type='general',
            )
            logger.info(
                'Emailed %s – missing: %s',
                user.email,
                ', '.join(missing_labels),
            )
        except Exception:
            logger.exception(
                'Failed to send incomplete-profile email to %s', user.email
            )
            raise

    return True
