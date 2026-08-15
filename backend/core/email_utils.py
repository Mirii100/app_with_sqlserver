import logging
from datetime import datetime as _datetime, time as _time
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa
from transactions.models import Transaction

logger = logging.getLogger(__name__)

CREDIT_TYPES = ('deposit', 'credit')
DEBIT_TYPES = ('withdrawal', 'debit')


def _day_start(date):
    """Aware start-of-day datetime for a date, or None."""
    if date is None:
        return None
    return timezone.make_aware(_datetime.combine(date, _time.min))


def _day_end(date):
    """Aware end-of-day datetime for a date, or None."""
    if date is None:
        return None
    return timezone.make_aware(_datetime.combine(date, _time.max))

def _statement_rows(user, from_date=None, to_date=None):
    """Return ordered statement rows with running balance plus totals.

    ``from_date``/``to_date`` (date objects) restrict the transactions that
    are included in the statement period.
    """
    txns = Transaction.objects.filter(user=user)
    if from_date is not None:
        txns = txns.filter(date__gte=_day_start(from_date))
    if to_date is not None:
        txns = txns.filter(date__lte=_day_end(to_date))
    transactions = list(txns.order_by('date', 'timestamp'))

    rows = []
    running_balance = Decimal('0.00')
    total_debits = Decimal('0.00')
    total_credits = Decimal('0.00')

    for txn in transactions:
        txn_type = (txn.type or '').lower()
        if txn_type in CREDIT_TYPES:
            credit = txn.amount
            debit = Decimal('0.00')
            total_credits += credit
        else:
            debit = txn.amount
            credit = Decimal('0.00')
            total_debits += debit

        running_balance += credit - debit

        rows.append({
            'date': txn.date,
            'description': txn.description or txn.category or 'Transaction',
            'reference': txn.reference or '',
            'debit': debit,
            'credit': credit,
            'balance': running_balance,
        })

    return rows, running_balance, total_debits, total_credits


def _format_period_label(rows):
    if not rows:
        return 'Full history'
    start = rows[0]['date'].strftime('%d %b %Y')
    end = rows[-1]['date'].strftime('%d %b %Y')
    if start == end:
        return f'{start}'
    return f'{start} - {end}'


def _period_label(from_date, to_date, rows):
    if from_date is not None or to_date is not None:
        start = from_date.strftime('%d %b %Y') if from_date else 'Beginning'
        end = to_date.strftime('%d %b %Y') if to_date else 'Today'
        if start == end:
            return start
        return f'{start} - {end}'
    return _format_period_label(rows)


def build_statement_pdf(user, from_date=None, to_date=None):
    """Render the user's transaction history into a PDF and return bytes.

    ``from_date``/``to_date`` restrict the transactions included.
    """
    rows, closing_balance, total_debits, total_credits = _statement_rows(
        user, from_date, to_date,
    )
    account = getattr(user, 'account', None)

    context = {
        'account_holder': user.get_full_name() or user.username,
        'account_number': (
            getattr(account, 'account_number', None) or user.account_number or ''
        ),
        'account_type': getattr(account, 'account_type', None) or 'savings',
        'currency': getattr(account, 'currency', None) or 'KSh',
        'generated_at': timezone.now(),
        'period_label': _period_label(from_date, to_date, rows),
        'rows': rows,
        'opening_balance': Decimal('0.00'),
        'closing_balance': closing_balance,
        'total_debits': total_debits,
        'total_credits': total_credits,
    }

    html = render_to_string('core/statement_pdf.html', context)

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if pisa_status.err:
        logger.error('Failed to render statement PDF for user %s', user.id)
        return None

    return buffer.getvalue()


def email_statement_to_user(user, from_date=None, to_date=None):
    """Email the user's account statement as a PDF attachment.

    ``from_date``/``to_date`` restrict the transactions included.
    Returns True when the email was handed to the SMTP backend.
    """
    if not user.email:
        logger.warning('User %s has no email address; skipping statement.', user.id)
        return False

    pdf_bytes = build_statement_pdf(user, from_date, to_date)
    if pdf_bytes is None:
        return False

    account = getattr(user, 'account', None)
    account_number = (
        getattr(account, 'account_number', None) or user.account_number or str(user.id)
    )

    if from_date is not None or to_date is not None:
        start = from_date.strftime('%d %b %Y') if from_date else 'the beginning'
        end = to_date.strftime('%d %b %Y') if to_date else 'today'
        period = f'{start} to {end}'
        coverage = f'It covers your transactions from {period}.'
    else:
        coverage = 'It covers your full transaction history.'

    subject = f'Your Alexia account statement ({timezone.now():%d %b %Y})'
    message = (
        f'Dear {user.get_full_name() or user.username},\n\n'
        f'Please find attached your account statement as of '
        f'{timezone.now():%d %B %Y}. {coverage}\n\n'
        f'If you did not request this statement, please contact support '
        f'immediately.\n\n— Alexia Financials'
    )

    return _send_statement_email(
        user, pdf_bytes, f'statement_{account_number}.pdf', subject, message,
    )


def build_stock_statement_pdf(user, from_date=None, to_date=None):
    """Render the user's shares portfolio + trading activity into a PDF.

    ``from_date``/``to_date`` restrict the trade history shown. The holdings
    table always reflects the current portfolio snapshot.
    Returns None when the user holds no shares.
    """
    from stocks.models import ShareHolding

    holdings = list(
        ShareHolding.objects
        .filter(user=user)
        .select_related('stock', 'wallet')
        .order_by('stock__code')
    )
    if not holdings:
        return None

    wallet = getattr(user, 'stock_wallet', None)

    rows = []
    total_cost = Decimal('0.00')
    total_value = Decimal('0.00')
    total_pnl = Decimal('0.00')
    for h in holdings:
        cost = h.cost_basis
        value = h.current_value
        pnl = value - cost
        total_cost += cost
        total_value += value
        total_pnl += pnl
        rows.append({
            'code': h.stock.code,
            'name': h.stock.name,
            'quantity': h.quantity,
            'avg_price': h.avg_price,
            'cost_basis': cost,
            'current_price': h.stock.current_price,
            'current_value': value,
            'pnl': pnl,
        })

    trades_qs = Transaction.objects.filter(user=user, category='shares')
    if from_date is not None:
        trades_qs = trades_qs.filter(date__gte=_day_start(from_date))
    if to_date is not None:
        trades_qs = trades_qs.filter(date__lte=_day_end(to_date))
    trades = list(trades_qs.order_by('-date'))

    context = {
        'account_holder': user.get_full_name() or user.username,
        'wallet_number': getattr(wallet, 'wallet_number', None) or '',
        'currency': 'KSh',
        'generated_at': timezone.now(),
        'period_label': _period_label(from_date, to_date, trades),
        'rows': rows,
        'total_cost_basis': total_cost,
        'total_value': total_value,
        'total_pnl': total_pnl,
        'trades': trades,
    }

    html = render_to_string('core/stock_statement_pdf.html', context)

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if pisa_status.err:
        logger.error('Failed to render stock statement PDF for user %s', user.id)
        return None

    return buffer.getvalue()


def build_loan_statement_pdf(user, from_date=None, to_date=None):
    """Render the user's loans + repayments into a PDF.

    ``from_date``/``to_date`` restrict which loans (created in the period)
    and repayments are shown.
    Returns None when the user has no loans.
    """
    from loans.models import Loan

    loans_qs = Loan.objects.filter(user=user).select_related('loan_product')
    if from_date is not None:
        loans_qs = loans_qs.filter(created_at__date__gte=from_date)
    if to_date is not None:
        loans_qs = loans_qs.filter(created_at__date__lte=to_date)
    loans = list(loans_qs.order_by('-created_at'))
    if not loans:
        return None

    rows = []
    total_borrowed = Decimal('0.00')
    total_approved = Decimal('0.00')
    total_outstanding = Decimal('0.00')
    for loan in loans:
        total_borrowed += loan.amount
        total_approved += loan.approved_amount
        total_outstanding += loan.outstanding_amount
        rows.append({
            'id': loan.id,
            'product': loan.loan_product.name if loan.loan_product else None,
            'amount': loan.amount,
            'approved_amount': loan.approved_amount,
            'outstanding': loan.outstanding_amount,
            'interest_rate': loan.interest_rate,
            'duration_months': loan.duration_months,
            'status': loan.get_status_display(),
            'created': loan.created_at,
        })

    repay_qs = Transaction.objects.filter(loan__in=loans, loan__isnull=False)
    if from_date is not None:
        repay_qs = repay_qs.filter(date__gte=_day_start(from_date))
    if to_date is not None:
        repay_qs = repay_qs.filter(date__lte=_day_end(to_date))
    repayments = list(
        repay_qs.select_related('loan').order_by('date', 'timestamp')
    )

    # Reconstruct the outstanding balance over time, per loan.
    remaining = {}
    for loan in loans:
        remaining[loan.id] = (
            loan.approved_amount if loan.approved_amount and loan.approved_amount > 0
            else loan.amount
        )
    repayment_rows = []
    for r in repayments:
        remaining[r.loan_id] = remaining.get(r.loan_id, Decimal('0.00')) - r.amount
        repayment_rows.append({
            'date': r.date,
            'description': r.description,
            'reference': r.reference,
            'amount': r.amount,
            'balance': sum(remaining.values()),
        })

    context = {
        'account_holder': user.get_full_name() or user.username,
        'currency': 'KSh',
        'generated_at': timezone.now(),
        'period_label': _period_label(from_date, to_date, repayment_rows),
        'rows': rows,
        'total_borrowed': total_borrowed,
        'total_approved': total_approved,
        'total_outstanding': total_outstanding,
        'repayments': repayment_rows,
    }

    html = render_to_string('core/loan_statement_pdf.html', context)

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if pisa_status.err:
        logger.error('Failed to render loan statement PDF for user %s', user.id)
        return None

    return buffer.getvalue()


def _send_statement_email(user, pdf_bytes, filename, subject, message):
    if not user.email:
        logger.warning('User %s has no email address; skipping statement.', user.id)
        return False

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach(filename, pdf_bytes, 'application/pdf')

    try:
        email.send(fail_silently=False)
    except Exception as e:
        logger.warning('Failed to send statement email to %s: %s', user.email, e)
        return False

    return True


def email_stock_statement_to_user(user, from_date=None, to_date=None):
    """Email the user's shares statement as a PDF attachment.

    ``from_date``/``to_date`` restrict the trade history shown.
    Returns False when the user holds no shares or has no email address.
    """
    if not user.email:
        logger.warning('User %s has no email address; skipping stock statement.', user.id)
        return False

    pdf_bytes = build_stock_statement_pdf(user, from_date, to_date)
    if pdf_bytes is None:
        return False

    wallet = getattr(user, 'stock_wallet', None)
    wallet_number = getattr(wallet, 'wallet_number', None) or str(user.id)

    subject = f'Your Alexia shares statement ({timezone.now():%d %b %Y})'
    message = (
        f'Dear {user.get_full_name() or user.username},\n\n'
        f'Please find attached your shares portfolio statement as of '
        f'{timezone.now():%d %B %Y}.\n\n'
        f'If you did not request this statement, please contact support '
        f'immediately.\n\n— Alexia Financials'
    )

    return _send_statement_email(
        user, pdf_bytes, f'shares_statement_{wallet_number}.pdf', subject, message,
    )


def email_loan_statement_to_user(user, from_date=None, to_date=None):
    """Email the user's loan statement as a PDF attachment.

    ``from_date``/``to_date`` restrict the loans and repayments shown.
    Returns False when the user has no loans or has no email address.
    """
    if not user.email:
        logger.warning('User %s has no email address; skipping loan statement.', user.id)
        return False

    pdf_bytes = build_loan_statement_pdf(user, from_date, to_date)
    if pdf_bytes is None:
        return False

    subject = f'Your Alexia loan statement ({timezone.now():%d %b %Y})'
    message = (
        f'Dear {user.get_full_name() or user.username},\n\n'
        f'Please find attached your loan statement as of '
        f'{timezone.now():%d %B %Y}.\n\n'
        f'If you did not request this statement, please contact support '
        f'immediately.\n\n— Alexia Financials'
    )

    return _send_statement_email(
        user, pdf_bytes, f'loan_statement_{user.account_number or user.id}.pdf',
        subject, message,
    )


def eligible_users(statement_type, from_date=None, to_date=None):
    """Return the QuerySet of users to email for a statement run.

    With a date range, only users with matching activity in the period are
    included (transactions for ``account``, share trades for ``stocks``, and
    loans created or repaid for ``loans``). Without a range, everyone with an
    email address qualifies for ``account``, users holding shares for
    ``stocks``, and users with loans for ``loans``.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    base = User.objects.filter(email__isnull=False)

    if statement_type == 'stocks':
        if from_date is not None or to_date is not None:
            trades = Transaction.objects.filter(category='shares')
            if from_date is not None:
                trades = trades.filter(date__gte=_day_start(from_date))
            if to_date is not None:
                trades = trades.filter(date__lte=_day_end(to_date))
            return base.filter(id__in=trades.values('user_id'))
        return base.filter(share_holdings__isnull=False).distinct()

    if statement_type == 'loans':
        from loans.models import Loan
        if from_date is not None or to_date is not None:
            loans = Loan.objects.all()
            if from_date is not None:
                loans = loans.filter(created_at__date__gte=from_date)
            if to_date is not None:
                loans = loans.filter(created_at__date__lte=to_date)
            repayments = Transaction.objects.filter(loan__isnull=False)
            if from_date is not None:
                repayments = repayments.filter(date__gte=_day_start(from_date))
            if to_date is not None:
                repayments = repayments.filter(date__lte=_day_end(to_date))
            ids = set(loans.values_list('user_id', flat=True))
            ids |= set(repayments.values_list('user_id', flat=True))
            return base.filter(id__in=ids)
        return base.filter(loans__isnull=False).distinct()

    # account
    if from_date is not None or to_date is not None:
        txns = Transaction.objects.all()
        if from_date is not None:
            txns = txns.filter(date__gte=_day_start(from_date))
        if to_date is not None:
            txns = txns.filter(date__lte=_day_end(to_date))
        return base.filter(id__in=txns.values('user_id'))
    return base
