from django.db import migrations

NSE_STOCKS = [
    ('SCOM', 'Safaricom PLC', 'Telecommunications', '19.05', '18.95'),
    ('EQTY', 'Equity Group Holdings PLC', 'Banking', '54.50', '53.75'),
    ('KCB', 'KCB Group PLC', 'Banking', '52.25', '51.80'),
    ('COOP', 'Co-operative Bank of Kenya PLC', 'Banking', '16.75', '16.50'),
    ('ABSA', 'Absa Bank Kenya PLC', 'Banking', '14.90', '14.70'),
    ('NCBA', 'NCBA Group PLC', 'Banking', '58.00', '57.25'),
    ('EABL', 'East African Breweries PLC', 'Beverages', '155.00', '153.50'),
    ('BAT', 'British American Tobacco Kenya PLC', 'Consumer Goods', '420.00', '418.00'),
    ('NMG', 'Nation Media Group PLC', 'Media', '15.00', '15.20'),
    ('TOTL', 'TotalEnergies Marketing Kenya PLC', 'Energy', '27.00', '26.50'),
    ('KEGN', 'Kenya Electricity Generating Company PLC', 'Energy', '3.90', '3.85'),
    ('KPLC', 'Kenya Power & Lighting Company PLC', 'Energy', '1.60', '1.55'),
    ('CICB', 'CIC Insurance Group PLC', 'Insurance', '2.90', '2.85'),
    ('BAMB', 'Bamburi Cement PLC', 'Construction', '47.00', '46.50'),
    ('SASN', 'Sasini PLC', 'Agriculture', '19.00', '18.90'),
    ('CTUM', 'Centum Investment Company PLC', 'Investment', '11.50', '11.35'),
    ('CARB', 'Carbacid Investments PLC', 'Chemicals', '17.50', '17.30'),
    ('KUKZ', 'Kakuzi PLC', 'Agriculture', '460.00', '455.00'),
    ('UMME', 'Umeme Limited', 'Energy', '14.00', '13.80'),
    ('LBTY', 'Liberty Kenya Holdings PLC', 'Insurance', '6.00', '5.90'),
]


def seed_stocks(apps, schema_editor):
    Stock = apps.get_model('stocks', 'Stock')
    db_alias = schema_editor.connection.alias
    for code, name, sector, price, previous in NSE_STOCKS:
        Stock.objects.using(db_alias).update_or_create(
            code=code,
            defaults={
                'name': name,
                'sector': sector,
                'current_price': price,
                'previous_close': previous,
                'is_active': True,
            },
        )


def unseed_stocks(apps, schema_editor):
    Stock = apps.get_model('stocks', 'Stock')
    db_alias = schema_editor.connection.alias
    Stock.objects.using(db_alias).filter(
        code__in=[code for code, *_ in NSE_STOCKS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_stocks, reverse_code=unseed_stocks),
    ]
