from django.db import migrations
from decimal import Decimal


def seed(apps, schema_editor):
    FxRate = apps.get_model('transactions', 'FxRate')
    CryptoAsset = apps.get_model('transactions', 'CryptoAsset')

    rates = [
        ('USD', Decimal('141.8500')),
        ('EUR', Decimal('165.4000')),
        ('GBP', Decimal('195.1200')),
    ]
    for code, rate in rates:
        FxRate.objects.update_or_create(
            code=code,
            defaults={'rate': rate, 'previous_rate': rate, 'is_active': True},
        )

    assets = [
        ('BTC', 'Bitcoin', '₿', '#F7931A', Decimal('14250000.00')),
        ('ETH', 'Ethereum', 'Ξ', '#627EEA', Decimal('580000.00')),
        ('USDT', 'Tether', '₮', '#26A17B', Decimal('141.85')),
    ]
    for symbol, name, glyph, color, price in assets:
        CryptoAsset.objects.update_or_create(
            symbol=symbol,
            defaults={
                'name': name,
                'glyph': glyph,
                'color_hex': color,
                'price_kes': price,
                'previous_price_kes': price,
                'is_active': True,
            },
        )


def unseed(apps, schema_editor):
    FxRate = apps.get_model('transactions', 'FxRate')
    CryptoAsset = apps.get_model('transactions', 'CryptoAsset')
    FxRate.objects.filter(code__in=['USD', 'EUR', 'GBP']).delete()
    CryptoAsset.objects.filter(symbol__in=['BTC', 'ETH', 'USDT']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0010_cryptoasset_fxrate_chequebookrequest_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
