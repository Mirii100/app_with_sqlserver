from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from investments.models import accrue_user_investments

User = get_user_model()


class Command(BaseCommand):
    help = 'Compute and deposit daily interest on open-ended (money market) investments.'

    def handle(self, *args, **options):
        total = Decimal('0')
        count = 0
        for user in User.objects.filter(investments__status='active').distinct():
            deposited = accrue_user_investments(user)
            if deposited > 0:
                count += 1
                total += deposited
        self.stdout.write(self.style.SUCCESS(
            f'Deposited KSh {total} of daily interest across {count} user(s).'
        ))
