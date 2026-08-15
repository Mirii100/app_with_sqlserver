from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from core.email_utils import (
    eligible_users,
    email_statement_to_user,
    email_stock_statement_to_user,
    email_loan_statement_to_user,
)

STATEMENT_TYPES = ('account', 'stocks', 'loans')


def _parse_date(value, name):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise CommandError(f'--{name} must be in YYYY-MM-DD format, got {value!r}.')


class Command(BaseCommand):
    help = (
        'Email a PDF statement to every eligible user. '
        '--type account (default) emails account statements, stocks emails '
        'only users who hold shares, loans emails only users who have loans. '
        'Use --from/--to to restrict both the statement period and the '
        'recipients (users with matching activity in the range). '
        'Use --user to target a single user (e.g. from a scheduler).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=STATEMENT_TYPES,
            default='account',
            help='Which statement type to send (default: account).',
        )
        parser.add_argument(
            '--user',
            type=int,
            help='Only email the user with this ID.',
        )
        parser.add_argument(
            '--from',
            dest='from_date',
            help='Only users active from this date (YYYY-MM-DD).',
        )
        parser.add_argument(
            '--to',
            dest='to_date',
            help='Only users active up to this date (YYYY-MM-DD).',
        )

    def handle(self, *args, **options):
        statement_type = options['type']
        from_date = _parse_date(options['from_date'], 'from')
        to_date = _parse_date(options['to_date'], 'to')

        users = eligible_users(statement_type, from_date, to_date)

        if options['user'] is not None:
            users = users.filter(id=options['user'])

        senders = {
            'account': email_statement_to_user,
            'stocks': email_stock_statement_to_user,
            'loans': email_loan_statement_to_user,
        }
        send = senders[statement_type]

        sent = 0
        failed = 0
        for user in users:
            if not user.email:
                continue
            if send(user, from_date, to_date):
                sent += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Sent {statement_type} statement to {user.email}'
                ))
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f'Failed to send {statement_type} statement to {user.email}'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Done. Type: {statement_type}. Sent: {sent}, failed: {failed}'
        ))
