from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import User
from insights.models import FinancialAdvice
from investments.models import Investment
from loans.models import Loan
from transactions.models import Budget


class Command(BaseCommand):
    help = 'Generates personalised financial advice rows for every user.'

    def handle(self, *args, **options):
        created = 0
        now = timezone.now()
        month_key = now.strftime('%Y-%m')

        for user in User.objects.filter(is_active=True):
            suggestions = []

            if user.balance <= 0:
                suggestions.append((
                    FinancialAdvice.AdviceType.SAVINGS,
                    'Build a safety net',
                    'Your main balance is empty. Try setting aside even a small '
                    'amount each week into savings so you are covered for surprises.',
                ))
            elif user.balance < 5000:
                suggestions.append((
                    FinancialAdvice.AdviceType.SAVINGS,
                    'Top up your buffer',
                    'Your balance is below KSh 5,000. A small emergency cushion '
                    'helps you avoid expensive quick loans when bills hit early.',
                ))

            active_loans = Loan.objects.filter(user=user, status='active').count()
            if user.loan_used > 0 or active_loans > 0:
                suggestions.append((
                    FinancialAdvice.AdviceType.DEBT,
                    'Retire your debt first',
                    'Debt costs you more than most investments earn. Paying off '
                    'your highest-rate loan first clears it faster and saves the most interest.',
                ))

            investments = Investment.objects.filter(user=user, status='active')
            if investments.exists():
                suggestions.append((
                    FinancialAdvice.AdviceType.INVESTMENT,
                    'Keep your money growing',
                    f'You have {investments.count()} active investment(s). Reviewing '
                    'them every quarter keeps your returns on track with your goals.',
                ))
            elif user.balance >= 10000:
                suggestions.append((
                    FinancialAdvice.AdviceType.INVESTMENT,
                    'Make your money work',
                    'You have enough balance to start investing. Even a money market '
                    'fund earns daily interest while keeping your cash accessible.',
                ))

            budget = Budget.objects.filter(user=user, month=month_key).first()
            if budget:
                spent = sum(
                    v for v in budget.get_categories().values()
                    if isinstance(v, (int, float))
                )
                limit = sum(
                    v for v in budget.get_budget_limits().values()
                    if isinstance(v, (int, float))
                )
                if limit > 0 and spent > limit:
                    suggestions.append((
                        FinancialAdvice.AdviceType.SPENDING,
                        'You overspent this month',
                        f'You spent about KSh {spent - limit} over your KSh {limit} '
                        'budget. Trim one discretionary category next month to get '
                        'back on track.',
                    ))

            if not suggestions:
                suggestions.append((
                    FinancialAdvice.AdviceType.GENERAL,
                    'Looking good',
                    'Your balances and activity look healthy. Keep monitoring '
                    'your spending and review your budget at the start of each month.',
                ))

            for advice_type, title, message in suggestions:
                exists = FinancialAdvice.objects.filter(
                    user=user,
                    title=title,
                    created_at__date=now.date(),
                ).exists()
                if exists:
                    continue
                FinancialAdvice.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    advice_type=advice_type,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} advice items.'))
