"""Management command to email users with incomplete profile data.

Checks each user for missing or empty required fields (phone number,
national ID, full name, county, town, employment type) and sends a
personalised email listing the fields that need updating.  Also creates
an in-app notification so the user sees the reminder inside the app.

Run daily via cron or a task scheduler, e.g.::

    python manage.py notify_incomplete_profiles
"""

import logging

from django.core.management.base import BaseCommand

from core.models import User
from core.utils import find_users_with_incomplete_profiles, notify_user_incomplete_profile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Emails users whose profile is missing required fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually emailing anyone',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        users = User.objects.filter(
            email__isnull=False,
        ).exclude(email='')

        results = find_users_with_incomplete_profiles(users)

        notified = 0
        for result in results:
            missing_labels = result.missing_labels
            try:
                if notify_user_incomplete_profile(
                    result.user, missing_labels, dry_run=dry_run
                ):
                    notified += 1
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'[DRY RUN] Would email {result.user.email} '
                                f'– missing: {", ".join(missing_labels)}'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Emailed {result.user.email} '
                                f'– missing: {", ".join(missing_labels)}'
                            )
                        )
            except Exception:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to email {result.user.email}'
                    )
                )

        skipped = len(users) - len(results)
        self.stdout.write(self.style.SUCCESS(
            f'Done. Notified {notified} users, skipped {skipped} '
            f'complete profiles.'
        ))
