"""Notifies users whose phone number is too short (invalid length).

Sends both an email and an in-app notification.  Intended to be run
periodically (e.g. daily via cron) to catch users who signed up with
an incomplete phone number.

    python manage.py notify_invalid_phones
"""

import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from notifications.models import Notification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Emails and notifies users with invalid phone number length'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually emailing anyone',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        User = get_user_model()
        users_to_notify = User.objects.filter(
            phone_number__isnull=False,
        ).exclude(phone_number='')

        count = 0
        for user in users_to_notify:
            if len(user.phone_number) < 10:
                if not user.email:
                    self.stdout.write(
                        self.style.WARNING(
                            f'User {user.username} has no email; '
                            f'skipping email, creating notification only'
                        )
                    )

                message = (
                    f'Dear {user.get_full_name() or user.username},\n\n'
                    f'We noticed that the phone number registered on your '
                    f'Alexia account ({user.phone_number}) appears to be '
                    f'incomplete. To ensure you can receive OTP codes, '
                    f'transaction alerts and other important notifications, '
                    f'please update your phone number in your profile '
                    f'settings.\n\n'
                    f'– Alexia Financials Team'
                )

                if not dry_run:
                    if user.email:
                        try:
                            send_mail(
                                'Action Required: Update Your Phone Number',
                                message,
                                settings.DEFAULT_FROM_EMAIL,
                                [user.email],
                                fail_silently=False,
                            )
                        except Exception as exc:
                            logger.warning(
                                'Failed to send phone-number update email '
                                'to %s: %s', user.email, exc,
                            )

                    Notification.objects.create(
                        user=user,
                        title='Action Required: Update Phone Number',
                        message=(
                            'Your registered phone number is incomplete. '
                            'Please update it in your profile settings to '
                            'ensure continued service.'
                        ),
                        type='general',
                    )

                count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Notified user: {user.username} '
                        f'({user.email or "no email"})'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully notified {count} users.')
        )
