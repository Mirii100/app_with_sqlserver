"""General transaction charge rules for AlexiaFinancials.

Charges are tiered by transaction value:

* <= 100            : no charge
* 101 .. 500       : 5%  transaction charge + 1%   government tax
* 501 .. 10000     : 8%  transaction charge + 1.25% government tax
* above 10000      : 8% base + 1% extra + 0.25% extra government tax for
                     every additional KSh 10,000 band

Every charge is recorded on a ``CompanyRevenue`` row tagged as revenue for
``AlexiaFinancials``, with a snapshot of the wider system balances at the
moment the charge is collected.
"""
from decimal import Decimal

from django.db.models import Sum

from .models import CompanyRevenue


def _money(value):
    return value.quantize(Decimal('0.01'))


# --- Charge tiers -----------------------------------------------------------
# (upper_bound_inclusive, broker_fee_percent, government_tax_percent)
TIER_ZERO_BAND = Decimal('100.00')
TIER_LOW_MAX = Decimal('500.00')
TIER_MID_MAX = Decimal('10000.00')

BROKER_LOW = Decimal('5.00')
TAX_LOW = Decimal('1.00')
BROKER_MID = Decimal('8.00')
TAX_MID = Decimal('1.25')
BROKER_HIGH_STEP = Decimal('1.00')
TAX_HIGH_STEP = Decimal('0.25')

CHAMA_FLAT_FEE = Decimal('200.00')


def compute_tiered_charges(value):
    """Return (broker_fee, gov_tax, broker_rate, tax_rate) for a value.

    ``value`` is the transaction amount (Decimal). No charge is applied when
    the value is <= 100."""
    if value is None:
        value = Decimal('0')
    value = Decimal(str(value))
    if value <= TIER_ZERO_BAND:
        return Decimal('0.00'), Decimal('0.00'), Decimal('0.00'), Decimal('0.00')

    if value <= TIER_LOW_MAX:
        broker_rate, tax_rate = BROKER_LOW, TAX_LOW
    elif value <= TIER_MID_MAX:
        broker_rate, tax_rate = BROKER_MID, TAX_MID
    else:
        bands = (value - TIER_MID_MAX) / Decimal('10000')
        bands = bands.to_integral_value(rounding='ROUND_FLOOR')
        # count of complete 10,000 bands above the 10,000 threshold
        extra = int(bands)
        broker_rate = BROKER_MID + extra * BROKER_HIGH_STEP
        tax_rate = TAX_MID + extra * TAX_HIGH_STEP

    broker_fee = _money(value * broker_rate / Decimal('100'))
    gov_tax = _money(value * tax_rate / Decimal('100'))
    return broker_fee, gov_tax, broker_rate, tax_rate


def _snapshot_totals(existing_charges=Decimal('0')):
    """Aggregate figures captured at charge time for the ledger columns."""
    # Late import to avoid a circular import at module load time.
    from transactions.models import SavingsGoal
    from chamas.models import ChamaMembership
    from .models import StockWallet

    investor_balances_total = (
        StockWallet.objects.aggregate(_t=Sum('balance'))['_t'] or Decimal('0')
    )
    goals_total = SavingsGoal.objects.aggregate(_t=Sum('saved_amount'))['_t'] or Decimal('0')
    chamas_total = (
        ChamaMembership.objects.aggregate(_t=Sum('contributed_amount'))['_t'] or Decimal('0')
    )
    app_total_charges = _money(existing_charges)

    return {
        'investor_balances_total': _money(investor_balances_total),
        'total_invested_goals': _money(goals_total),
        'total_invested_chamas': _money(chamas_total),
        'total_invested_stocks': _money(investor_balances_total),
        'app_total_charges': app_total_charges,
    }


def record_charges(user, charge_category, charge_type, txn, value,
                    account_number=None, broker_fee=None, gov_tax=None,
                    broker_rate=None, tax_rate=None, flat_fee=None):
    """Record charge(s) as CompanyRevenue rows for ``AlexiaFinancials``.

    Either tiered fees (``broker_fee``/``gov_tax`` computed from ``value`` if
    not supplied) or a single ``flat_fee`` (mandatory chama account fee) may be
    recorded. ``total_collected`` is the gross value moved by the user.
    """
    if flat_fee is not None and flat_fee > 0:
        flat_fee = _money(flat_fee)
        rows = [('chama_fee', flat_fee, Decimal('0.00'))]
        total_charges = flat_fee
    else:
        if broker_fee is None or gov_tax is None:
            broker_fee, gov_tax, broker_rate, tax_rate = compute_tiered_charges(value)
        if broker_fee == 0 and gov_tax == 0:
            return {
                'broker_fee': Decimal('0.00'),
                'government_tax': Decimal('0.00'),
                'total_charges': Decimal('0.00'),
                'broker_rate': Decimal('0.000'),
                'tax_rate': Decimal('0.00'),
            }
        broker_fee = _money(broker_fee)
        gov_tax = _money(gov_tax)
        rows = [
            ('broker_fee', broker_fee, broker_rate),
            ('government_tax', gov_tax, tax_rate),
        ]
        total_charges = _money(broker_fee + gov_tax)

    prior = (
        CompanyRevenue.objects
        .aggregate(_t=Sum('amount'))['_t'] or Decimal('0')
    )
    snap = _snapshot_totals(existing_charges=prior + total_charges)

    base = dict(
        company='AlexiaFinancials',
        charge_type=charge_type,
        user=user,
        account_number=account_number or '',
        transaction=txn,
        total_collected=_money(value),
        outflow=Decimal('0.00'),
        app_total_charges=snap['app_total_charges'],
        investor_balances_total=snap['investor_balances_total'],
        total_invested_goals=snap['total_invested_goals'],
        total_invested_chamas=snap['total_invested_chamas'],
        total_invested_stocks=snap['total_invested_stocks'],
        user_deposit_balance=_money(user.balance),
    )

    if rows[0][0] == 'chama_fee':
        CompanyRevenue.objects.create(
            source='chama_fee', amount=rows[0][1],
            charge_rate=Decimal('0.000'), trade_type='debit', **base,
        )
    else:
        CompanyRevenue.objects.create(
            source='broker_fee', amount=rows[0][1],
            charge_rate=rows[0][2], trade_type='debit', **base,
        )
        CompanyRevenue.objects.create(
            source='government_tax', amount=rows[1][1],
            charge_rate=rows[1][2], trade_type='debit', **base,
        )

    return {
        'broker_fee': rows[0][1] if rows[0][0] == 'broker_fee' else Decimal('0.00'),
        'government_tax': rows[1][1] if len(rows) > 1 and rows[1][0] == 'government_tax' else Decimal('0.00'),
        'total_charges': total_charges,
        'broker_rate': broker_rate or Decimal('0.000'),
        'tax_rate': tax_rate or Decimal('0.00'),
    }
