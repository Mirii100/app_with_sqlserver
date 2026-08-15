from datetime import datetime

from django.contrib import admin
from django.shortcuts import render

from .email_utils import (
    eligible_users,
    email_statement_to_user,
    email_stock_statement_to_user,
    email_loan_statement_to_user,
)

STATEMENT_TYPES = ('account', 'stocks', 'loans')

SENDERS = {
    'account': email_statement_to_user,
    'stocks': email_stock_statement_to_user,
    'loans': email_loan_statement_to_user,
}


def _parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return None


def send_statements_view(request):
    """Staff-only page to filter by type + date and email statements."""
    form = {'type': 'account', 'from_date': '', 'to_date': ''}
    results = None
    submitted = False
    sent = failed = 0
    error = None

    if request.method == 'POST':
        statement_type = request.POST.get('type', 'account')
        if statement_type not in STATEMENT_TYPES:
            statement_type = 'account'
        from_raw = (request.POST.get('from_date') or '').strip()
        to_raw = (request.POST.get('to_date') or '').strip()
        from_date = _parse_date(from_raw)
        to_date = _parse_date(to_raw)

        form.update({
            'type': statement_type,
            'from_date': from_raw,
            'to_date': to_raw,
        })

        if from_raw and from_date is None:
            error = 'From date must be in YYYY-MM-DD format.'
        elif to_raw and to_date is None:
            error = 'To date must be in YYYY-MM-DD format.'
        elif from_date and to_date and from_date > to_date:
            error = 'From date must not be after the to date.'
        else:
            submitted = True
            users = list(eligible_users(statement_type, from_date, to_date))
            send = SENDERS[statement_type]
            results = []
            for user in users:
                if not user.email:
                    continue
                if send(user, from_date, to_date):
                    sent += 1
                    results.append({
                        'user': user.get_full_name() or user.username,
                        'email': user.email,
                        'status': 'Sent',
                    })
                else:
                    failed += 1
                    results.append({
                        'user': user.get_full_name() or user.username,
                        'email': user.email,
                        'status': 'Failed',
                    })
    else:
        requested_type = request.GET.get('type')
        if requested_type in STATEMENT_TYPES:
            form['type'] = requested_type

    counts = {}
    for statement_type in STATEMENT_TYPES:
        counts[statement_type] = eligible_users(statement_type).count()

    context = admin.site.each_context(request)
    context.update({
        'title': 'Send statements',
        'form': form,
        'counts': counts,
        'results': results,
        'submitted': submitted,
        'sent': sent,
        'failed': failed,
        'error': error,
    })
    return render(request, 'admin/statement_send.html', context)
