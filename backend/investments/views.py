from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from transactions.models import Transaction

from .models import (
    Investment,
    InvestmentProduct,
    InvestmentReturn,
    InvestmentWallet,
    accrue_investment,
    accrue_user_investments,
)
from .serializers import InvestmentProductSerializer, InvestmentSerializer


class InvestmentProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Active investment products with dynamically computed rates."""

    serializer_class = InvestmentProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InvestmentProduct.objects.filter(is_active=True)

    @action(detail=True, methods=['post'])
    def quote(self, request, pk=None):
        product = self.get_object()
        amount = request.data.get('amount')
        if amount is None:
            return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        if amount < product.min_amount:
            return Response(
                {'error': f'Minimum investment for this product is KSh {product.min_amount}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(product.compute(amount))


class InvestmentViewSet(viewsets.ModelViewSet):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='invest')
    def invest(self, request):
        user = request.user
        product_id = request.data.get('product_id') or request.data.get('product')
        amount = request.data.get('amount')

        if not product_id or not amount:
            return Response(
                {'error': 'product_id and amount are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = InvestmentProduct.objects.get(id=product_id, is_active=True)
        except InvestmentProduct.DoesNotExist:
            return Response(
                {'error': 'Investment product not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount < product.min_amount:
            return Response(
                {'error': f'Minimum investment for this product is KSh {product.min_amount}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.balance < amount:
            return Response(
                {'error': 'Insufficient balance. Please top up your account first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        calc = product.compute(amount)
        if product.product_type == InvestmentProduct.ProductType.MONEY_MARKET_FUND:
            maturity_date = None
            last_accrual_date = timezone.now()
        else:
            maturity_date = timezone.now() + timezone.timedelta(days=product.tenure_days)
            last_accrual_date = None

        with transaction.atomic():
            wallet, _ = InvestmentWallet.objects.get_or_create(
                user=user,
                product_type=product.product_type,
            )

            user.balance -= amount
            user.save(update_fields=['balance'])

            wallet.balance += amount
            wallet.save(update_fields=['balance'])

            investment = Investment.objects.create(
                user=user,
                product=product,
                wallet=wallet,
                amount=calc['amount'],
                maturity_value=calc['maturity_value'],
                fee_deducted=calc['fee_deducted'],
                net_payout=calc['net_payout'],
                interest_accrued=Decimal('0.00'),
                last_accrual_date=last_accrual_date,
                maturity_date=maturity_date,
            )

            Transaction.objects.create(
                user=user,
                amount=calc['amount'],
                category='investment',
                type='withdrawal',
                description=f'Invested in {product.name} (wallet {wallet.wallet_number})',
                date=timezone.now(),
            )

            from rewards.points import award_points
            award_points(
                user,
                'investment',
                key=f'investment:{investment.id}',
                description=f'Invested KSh {calc["amount"]} in {product.name}',
            )

        return Response({
            'status': 'success',
            'investment': InvestmentSerializer(investment).data,
            'quote': calc,
            'wallet': {
                'wallet_number': wallet.wallet_number,
                'product_type': wallet.product_type,
                'balance': str(wallet.balance),
            },
            'new_balance': str(user.balance),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='portfolio')
    def portfolio(self, request):
        """Summary of what the user has invested: totals, growth and a
        per-product-type breakdown for charts. Money market interest accrued
        so far is computed and deposited first."""
        user = request.user
        accrue_user_investments(user)
        active = Investment.objects.filter(user=user, status='active').select_related('product')

        total_invested = Decimal('0')
        total_value = Decimal('0')
        breakdown = {}
        holdings = []

        for inv in active:
            current_value = inv.current_value()
            key = inv.product.product_type
            row = breakdown.setdefault(key, {
                'product_type': key,
                'name': inv.product.name,
                'invested': Decimal('0'),
                'current_value': Decimal('0'),
                'growth': Decimal('0'),
                'count': 0,
            })
            row['invested'] += inv.amount
            row['current_value'] += current_value
            row['count'] += 1
            total_invested += inv.amount
            total_value += current_value

            holdings.append({
                'id': inv.id,
                'product_name': inv.product.name,
                'product_type': key,
                'amount': str(inv.amount),
                'current_value': str(current_value),
                'interest_accrued': str(inv.interest_accrued),
                'status': inv.status,
                'invested_at': inv.invested_at.isoformat(),
                'maturity_date': inv.maturity_date.isoformat() if inv.maturity_date else None,
                'open_ended': inv.is_open_ended(),
            })

        for row in breakdown.values():
            row['growth'] = row['current_value'] - row['invested']
            row['invested'] = str(row['invested'])
            row['current_value'] = str(row['current_value'])
            row['growth'] = str(row['growth'])

        growth = total_value - total_invested
        growth_percent = Decimal('0.00')
        if total_invested:
            growth_percent = (growth / total_invested * Decimal('100')).quantize(Decimal('0.01'))

        return Response({
            'total_invested': str(total_invested),
            'current_value': str(total_value),
            'total_growth': str(growth),
            'growth_percent': str(growth_percent),
            'active_count': len(holdings),
            'breakdown': list(breakdown.values()),
            'holdings': holdings,
        })

    @action(detail=False, methods=['get'], url_path='returns')
    def returns(self, request):
        """All return events across the user's investments."""
        rows = InvestmentReturn.objects.filter(user=request.user).select_related(
            'investment__product'
        )
        return Response([{
            'id': r.id,
            'investment_id': r.investment_id,
            'product_name': r.investment.product.name,
            'return_type': r.return_type,
            'amount': str(r.amount),
            'description': r.description,
            'created_at': r.created_at.isoformat(),
        } for r in rows])

    @action(detail=True, methods=['get'], url_path='returns')
    def investment_returns(self, request, pk=None):
        """Return events for a single investment."""
        investment = self.get_object()
        rows = investment.returns.select_related('investment__product')
        return Response([{
            'id': r.id,
            'return_type': r.return_type,
            'amount': str(r.amount),
            'description': r.description,
            'created_at': r.created_at.isoformat(),
        } for r in rows])

    @action(detail=True, methods=['post'], url_path='redeem')
    def redeem(self, request, pk=None):
        investment = self.get_object()
        user = investment.user

        if investment.status != 'active':
            return Response(
                {'error': 'This investment has already been settled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_open_ended = investment.is_open_ended()
        if is_open_ended:
            accrue_investment(investment)
            payout = investment.amount + investment.interest_accrued
            wallet_debit = investment.amount + investment.interest_accrued
        else:
            if timezone.now() < investment.maturity_date:
                return Response(
                    {'error': f'Investment matures on {investment.maturity_date:%d %b %Y, %H:%M}. You cannot redeem before maturity.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payout = investment.net_payout
            wallet_debit = investment.amount

        with transaction.atomic():
            wallet = investment.wallet
            if wallet:
                wallet.balance -= wallet_debit
                wallet.save(update_fields=['balance'])

            user.balance += payout
            user.save(update_fields=['balance'])

            investment.status = 'completed'
            investment.save(update_fields=['status'])

            if is_open_ended:
                description = (f'{investment.product.name} payout '
                               f'(incl. KSh {investment.interest_accrued} accrued interest)')
            else:
                description = (f'{investment.product.name} payout '
                               f'(after deduction of KSh {investment.fee_deducted})')
            Transaction.objects.create(
                user=user,
                amount=payout,
                category='investment_redemption',
                type='deposit',
                description=description,
                date=timezone.now(),
            )
            InvestmentReturn.objects.create(
                user=user,
                investment=investment,
                return_type=(InvestmentReturn.ReturnType.REDEMPTION
                             if is_open_ended else InvestmentReturn.ReturnType.MATURITY),
                amount=payout,
                description=description,
            )

        return Response({
            'status': 'success',
            'payout': str(payout),
            'interest_accrued': str(investment.interest_accrued),
            'fee_deducted': str(investment.fee_deducted),
            'wallet': {
                'wallet_number': wallet.wallet_number if wallet else None,
                'product_type': investment.product.product_type,
                'balance': str(wallet.balance) if wallet else '0.00',
            },
            'new_balance': str(user.balance),
        })
