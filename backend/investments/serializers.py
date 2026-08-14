from decimal import Decimal

from rest_framework import serializers

from .models import Investment, InvestmentProduct

def _format_rate(value, suffix='% p.a.'):
    return f'{Decimal(str(value)).quantize(Decimal("0.01")).normalize()}{suffix}'


class InvestmentProductSerializer(serializers.ModelSerializer):
    display_description = serializers.SerializerMethodField()
    gross_rate = serializers.SerializerMethodField()
    rate_display = serializers.SerializerMethodField()
    daily_rate_display = serializers.SerializerMethodField()
    deduction_percent = serializers.SerializerMethodField()
    example = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentProduct
        fields = [
            'id',
            'name',
            'product_type',
            'tagline',
            'description',
            'annual_rate',
            'fee_percent',
            'tenure_days',
            'min_amount',
            'is_active',
            'is_best_match',
            'display_description',
            'gross_rate',
            'rate_display',
            'daily_rate_display',
            'deduction_percent',
            'example',
        ]

    def get_display_description(self, obj):
        return obj.get_display_description()

    def get_gross_rate(self, obj):
        return _format_rate(obj.annual_rate)

    def get_rate_display(self, obj):
        return _format_rate(obj.compute(obj.min_amount)['net_annualized_rate'])

    def get_daily_rate_display(self, obj):
        """Daily interest rate for funds that accrue daily.

        Money market funds (and unit trusts) earn interest on a daily basis.
        The net annual rate after the management fee is divided by 365 to get
        the nominal daily rate:  daily_rate = (annual_rate - fee_percent) / 365.
        On a KSh B balance the investor earns  B * daily_rate / 100 per day.
        Treasury bills are discount securities (no daily accrual), so they
        have no daily rate.
        """
        if obj.product_type in (
            InvestmentProduct.ProductType.MONEY_MARKET_FUND,
            InvestmentProduct.ProductType.BALANCED_UNIT_TRUST,
        ):
            net_annual = Decimal(str(obj.annual_rate)) - Decimal(str(obj.fee_percent))
            daily = (net_annual / Decimal('365')).quantize(Decimal('0.0001'))
            return f'{daily}% daily'
        return None

    def get_deduction_percent(self, obj):
        return f'{Decimal(str(obj.fee_percent)).quantize(Decimal("0.01")).normalize()}% deducted'

    def get_example(self, obj):
        return obj.compute(obj.min_amount)


class InvestmentSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_type = serializers.CharField(source='product.product_type', read_only=True)
    current_value = serializers.SerializerMethodField()
    open_ended = serializers.SerializerMethodField()

    class Meta:
        model = Investment
        fields = [
            'id',
            'product',
            'product_name',
            'product_type',
            'amount',
            'maturity_value',
            'fee_deducted',
            'net_payout',
            'interest_accrued',
            'current_value',
            'open_ended',
            'status',
            'invested_at',
            'maturity_date',
        ]
        read_only_fields = [
            'id',
            'amount',
            'maturity_value',
            'fee_deducted',
            'net_payout',
            'interest_accrued',
            'status',
            'invested_at',
            'maturity_date',
        ]

    def get_current_value(self, obj):
        return obj.current_value()

    def get_open_ended(self, obj):
        return obj.is_open_ended()
