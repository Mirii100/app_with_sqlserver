from decimal import Decimal

from django.db import migrations

from investments.models import InvestmentProduct


def seed_products(apps, schema_editor):
    Product = apps.get_model('investments', 'InvestmentProduct')
    ProductType = InvestmentProduct.ProductType

    defaults = [
        {
            'name': '91-Day Treasury Bill',
            'product_type': ProductType.TREASURY_BILL,
            'tagline': 'Government-backed',
            'annual_rate': Decimal('16.100'),
            'fee_percent': Decimal('0.500'),
            'tenure_days': 91,
            'min_amount': Decimal('3000.00'),
            'is_best_match': True,
        },
        {
            'name': 'Alexia Money Market Fund',
            'product_type': ProductType.MONEY_MARKET_FUND,
            'tagline': 'Withdraw anytime',
            'annual_rate': Decimal('11.400'),
            'fee_percent': Decimal('1.500'),
            'tenure_days': 30,
            'min_amount': Decimal('500.00'),
            'is_best_match': False,
        },
        {
            'name': 'Balanced Unit Trust',
            'product_type': ProductType.BALANCED_UNIT_TRUST,
            'tagline': 'Medium risk',
            'annual_rate': Decimal('9.800'),
            'fee_percent': Decimal('2.000'),
            'tenure_days': 365,
            'min_amount': Decimal('1000.00'),
            'is_best_match': False,
        },
    ]

    for data in defaults:
        Product.objects.update_or_create(
            name=data['name'],
            defaults=data,
        )


def remove_products(apps, schema_editor):
    Product = apps.get_model('investments', 'InvestmentProduct')
    Product.objects.filter(
        name__in=['91-Day Treasury Bill', 'Alexia Money Market Fund', 'Balanced Unit Trust']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_products, remove_products),
    ]
