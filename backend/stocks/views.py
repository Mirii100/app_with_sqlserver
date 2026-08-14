from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from transactions.models import Transaction, SavingsGoal

from chamas.models import ChamaMembership

from .models import CompanyRevenue, ShareHolding, Stock, StockWallet
from .serializers import StockSerializer

BROKER_FEE_PERCENT = Decimal('2.00')
GOVERNMENT_TAX_PERCENT = Decimal('0.10')


def _money(value):
    return value.quantize(Decimal('0.01'))


def _compute_charges(value):
    """Broker fee (2%) and government tax (0.1%) on a trade value."""
    broker_fee = _money(value * BROKER_FEE_PERCENT / Decimal('100'))
    gov_tax = _money(value * GOVERNMENT_TAX_PERCENT / Decimal('100'))
    total = _money(broker_fee + gov_tax)
    return broker_fee, gov_tax, total


def _record_revenue(user, stock, trade_type, wallet_number, transaction,
                    total_collected, broker_fee, gov_tax):
    # Snapshot of the company's investor-wallet balances at this moment.
    wallets = StockWallet.objects.all()
    investor_balances_total = (
        wallets.aggregate(_t=models.Sum('balance'))['_t'] or Decimal('0')
    )

    # Running total of all charges collected across every user (this charge included).
    prior_charges = CompanyRevenue.objects.aggregate(_t=models.Sum('amount'))['_t'] or Decimal('0')
    app_total_charges = _money(prior_charges + broker_fee + gov_tax)

    # System-wide totals of money users have invested outside/inside stocks.
    goals_total = SavingsGoal.objects.aggregate(_t=models.Sum('saved_amount'))['_t'] or Decimal('0')
    chamas_total = ChamaMembership.objects.aggregate(_t=models.Sum('contributed_amount'))['_t'] or Decimal('0')

    kwargs = dict(
        company='AlexiaFinancials',
        trade_type=trade_type,
        user=user,
        stock=stock,
        account_number=wallet_number,
        transaction=transaction,
        total_collected=total_collected,
        outflow=Decimal('0.00'),
        investor_balances_total=_money(investor_balances_total),
        user_deposit_balance=_money(user.balance),
        app_total_charges=app_total_charges,
        total_invested_goals=_money(goals_total),
        total_invested_chamas=_money(chamas_total),
        total_invested_stocks=_money(investor_balances_total),
    )
    CompanyRevenue.objects.create(
        source='broker_fee', amount=broker_fee, charge_type='stocks',
        charge_rate=BROKER_FEE_PERCENT, **kwargs)
    CompanyRevenue.objects.create(
        source='government_tax', amount=gov_tax, charge_type='stocks',
        charge_rate=GOVERNMENT_TAX_PERCENT, **kwargs)


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """Nairobi Securities Exchange stocks with a per-user shares wallet."""

    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Stock.objects.filter(is_active=True)

    @action(detail=False, methods=['get'], url_path='portfolio')
    def portfolio(self, request):
        """The user's shares wallet and current holdings."""
        user = request.user
        wallet = StockWallet.objects.filter(user=user).first()

        if wallet is None:
            return Response({
                'account_registered': False,
                'wallet_number': None,
                'wallet_balance': '0.00',
                'invested': '0.00',
                'current_value': '0.00',
                'pnl': '0.00',
                'pnl_percent': '0.00',
                'holdings': [],
            })

        holdings = ShareHolding.objects.filter(user=user).select_related('stock')

        total_invested = Decimal('0')
        total_value = Decimal('0')
        items = []
        for h in holdings:
            cv = h.current_value
            total_invested += h.cost_basis
            total_value += cv
            items.append({
                'stock': h.stock_id,
                'code': h.stock.code,
                'name': h.stock.name,
                'quantity': h.quantity,
                'avg_price': str(h.avg_price),
                'current_price': str(h.stock.current_price),
                'invested': str(h.cost_basis),
                'current_value': str(cv),
                'pnl': str(cv - h.cost_basis),
            })

        pnl = total_value - total_invested
        pnl_percent = Decimal('0.00')
        if total_invested:
            pnl_percent = (pnl / total_invested * Decimal('100')).quantize(Decimal('0.01'))

        return Response({
            'account_registered': True,
            'wallet_number': wallet.wallet_number,
            'wallet_balance': str(wallet.balance),
            'invested': str(total_invested),
            'current_value': str(total_value),
            'pnl': str(pnl),
            'pnl_percent': str(pnl_percent),
            'holdings': items,
        })

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        """Registers the user's separate shares account (wallet).

        Each user gets their own 12-digit wallet number (prefix '8'), separate
        from their normal account number. Calling this again is a no-op and
        simply returns the existing wallet."""
        user = request.user
        wallet, created = StockWallet.objects.get_or_create(user=user)
        return Response({
            'status': 'success',
            'created': created,
            'account_number': wallet.wallet_number,
            'wallet_number': wallet.wallet_number,
            'balance': str(wallet.balance),
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='quote')
    def quote(self, request, pk=None):
        """Charges and total for buying a quantity of shares.

        Buyers pay the stock value plus a 2% broker fee and a 0.1%
        government tax. Sellers receive the gross proceeds minus the same
        charges."""
        stock = self.get_object()
        raw = request.query_params.get('quantity')
        try:
            quantity = int(raw)
        except (TypeError, ValueError):
            return Response(
                {'error': 'quantity is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be greater than zero'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        stock_value = _money(stock.current_price * quantity)
        broker_fee, gov_tax, total_charges = _compute_charges(stock_value)
        return Response({
            'stock': stock.code,
            'quantity': quantity,
            'stock_value': str(stock_value),
            'broker_fee': str(broker_fee),
            'government_tax': str(gov_tax),
            'total_charges': str(total_charges),
            'total': str(_money(stock_value + total_charges)),
        })

    @action(detail=False, methods=['get'], url_path='revenue-summary')
    def revenue_summary(self, request):
        """Total revenue collected by AlexiaFinancials from share charges.

        Pass ``?detail=1`` for the per-charge audit rows (account number,
        transaction reference, user and date/time)."""
        rows = list(CompanyRevenue.objects.select_related('user', 'stock', 'transaction'))
        total = sum((r.amount for r in rows), Decimal('0'))
        by_source = {}
        by_trade = {}
        by_charge_type = {}
        for r in rows:
            by_source[r.source] = by_source.get(r.source, Decimal('0')) + r.amount
            by_trade[r.trade_type] = by_trade.get(r.trade_type, Decimal('0')) + r.amount
            by_charge_type[r.charge_type] = by_charge_type.get(r.charge_type, Decimal('0')) + r.amount
        summary = {
            'company': 'AlexiaFinancials',
            'total_revenue': str(total),
            'by_source': {k: str(v) for k, v in by_source.items()},
            'by_trade_type': {k: str(v) for k, v in by_trade.items()},
            'by_charge_type': {k: str(v) for k, v in by_charge_type.items()},
            'entries': len(rows),
        }
        if request.query_params.get('detail') == '1':
            summary['charges'] = [
                {
                    'source': r.source,
                    'amount': str(r.amount),
                    'charge_type': r.charge_type,
                    'charge_rate': str(r.charge_rate),
                    'trade_type': r.trade_type,
                    'account_number': r.account_number,
                    'user': r.user.username if r.user else None,
                    'stock': r.stock.code if r.stock else None,
                    'transaction_reference': r.transaction.reference if r.transaction else None,
                    'total_collected': str(r.total_collected),
                    'outflow': str(r.outflow),
                    'investor_balances_total': str(r.investor_balances_total),
                    'user_deposit_balance': str(r.user_deposit_balance),
                    'app_total_charges': str(r.app_total_charges),
                    'total_invested_goals': str(r.total_invested_goals),
                    'total_invested_chamas': str(r.total_invested_chamas),
                    'total_invested_stocks': str(r.total_invested_stocks),
                    'created_at': r.created_at.isoformat(),
                }
                for r in rows
            ]
        return Response(summary)

    @action(detail=True, methods=['post'], url_path='buy')
    def buy(self, request, pk=None):
        stock = self.get_object()
        user = request.user

        quantity = request.data.get('quantity')
        if quantity is None:
            return Response({'error': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({'error': 'Quantity must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        cost = stock.current_price * quantity

        stock_value = _money(cost)
        broker_fee, gov_tax, total_charges = _compute_charges(stock_value)
        total_cost = _money(stock_value + total_charges)

        wallet = StockWallet.objects.filter(user=user).first()
        if wallet is None:
            return Response(
                {'error': 'Register a stock account before buying shares. '
                          'Use the "Register stock account" option first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.balance < total_cost:
            return Response(
                {'error': 'Insufficient balance. Please top up your account first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.balance -= total_cost
            user.save(update_fields=['balance'])

            wallet.balance += stock_value
            wallet.save(update_fields=['balance'])

            holding, created = ShareHolding.objects.select_for_update().get_or_create(
                user=user,
                stock=stock,
                defaults={'wallet': wallet, 'quantity': quantity, 'avg_price': stock.current_price},
            )
            if not created:
                total_qty = holding.quantity + quantity
                new_avg = ((holding.avg_price * holding.quantity
                            + stock.current_price * quantity) / total_qty)
                holding.quantity = total_qty
                holding.avg_price = new_avg
                holding.wallet = wallet
                holding.save(update_fields=['quantity', 'avg_price', 'wallet'])

            tx = Transaction.objects.create(
                user=user,
                amount=total_cost,
                category='shares',
                type='withdrawal',
                description=f'Bought {quantity} shares of {stock.code} @ KSh {stock.current_price} '
                            f'(value KSh {stock_value}, charges KSh {total_charges}, '
                            f'total KSh {total_cost})',
                date=timezone.now(),
            )

            _record_revenue(user, stock, 'buy', wallet.wallet_number, tx,
                            total_cost, broker_fee, gov_tax)

        return Response({
            'status': 'success',
            'stock': stock.code,
            'quantity': quantity,
            'price': str(stock.current_price),
            'stock_value': str(stock_value),
            'broker_fee': str(broker_fee),
            'government_tax': str(gov_tax),
            'total_charges': str(total_charges),
            'total_cost': str(total_cost),
            'wallet': {
                'wallet_number': wallet.wallet_number,
                'balance': str(wallet.balance),
            },
            'new_balance': str(user.balance),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='sell')
    def sell(self, request, pk=None):
        stock = self.get_object()
        user = request.user

        quantity = request.data.get('quantity')
        if quantity is None:
            return Response({'error': 'quantity is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({'error': 'Quantity must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            holding = ShareHolding.objects.select_related('stock', 'wallet').get(user=user, stock=stock)
        except ShareHolding.DoesNotExist:
            return Response({'error': f'You do not hold any {stock.code} shares.'},
                            status=status.HTTP_400_BAD_REQUEST)

        if quantity > holding.quantity:
            return Response({'error': f'You only hold {holding.quantity} shares of {stock.code}.'},
                            status=status.HTTP_400_BAD_REQUEST)

        proceeds = stock.current_price * quantity
        cost_basis = holding.avg_price * quantity

        gross_value = _money(proceeds)
        broker_fee, gov_tax, total_charges = _compute_charges(gross_value)
        net_proceeds = _money(gross_value - total_charges)

        with transaction.atomic():
            wallet = holding.wallet

            user.balance += net_proceeds
            user.save(update_fields=['balance'])

            wallet.balance -= cost_basis
            wallet.save(update_fields=['balance'])

            if quantity == holding.quantity:
                holding.delete()
            else:
                holding.quantity -= quantity
                holding.save(update_fields=['quantity'])

            tx = Transaction.objects.create(
                user=user,
                amount=net_proceeds,
                category='shares',
                type='deposit',
                description=f'Sold {quantity} shares of {stock.code} @ KSh {stock.current_price} '
                            f'(value KSh {gross_value}, charges KSh {total_charges}, '
                            f'net KSh {net_proceeds}, profit KSh {net_proceeds - cost_basis})',
                date=timezone.now(),
            )

            _record_revenue(user, stock, 'sell', wallet.wallet_number, tx,
                            gross_value, broker_fee, gov_tax)

        return Response({
            'status': 'success',
            'stock': stock.code,
            'quantity': quantity,
            'price': str(stock.current_price),
            'gross_value': str(gross_value),
            'broker_fee': str(broker_fee),
            'government_tax': str(gov_tax),
            'total_charges': str(total_charges),
            'net_proceeds': str(net_proceeds),
            'cost_basis': str(cost_basis),
            'pnl': str(net_proceeds - cost_basis),
            'wallet': {
                'wallet_number': wallet.wallet_number,
                'balance': str(wallet.balance),
            },
            'new_balance': str(user.balance),
        })
