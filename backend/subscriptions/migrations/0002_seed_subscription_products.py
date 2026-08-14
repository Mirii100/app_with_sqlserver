from django.db import migrations


def seed_subscriptions(apps, schema_editor):
    Subscription = apps.get_model('subscriptions', 'Subscription')

    products = [
        {
            'name': 'Netflix',
            'description': 'Streaming movies and series',
            'price': '1100.00',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'DSTV',
            'description': 'Satellite TV packages',
            'price': '2010.00',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'Gym membership',
            'description': 'Monthly gym subscription',
            'price': '1750.00',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'Spotify',
            'description': 'Music streaming service',
            'price': '499.00',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'Apple Music',
            'description': 'Music streaming service',
            'price': '599.00',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'iCloud+',
            'description': 'Cloud storage subscription',
            'price': '150.00',
            'billing_cycle': 'monthly',
        },
        {
            'name': 'Showmax',
            'description': 'Streaming service',
            'price': '850.00',
            'billing_cycle': 'monthly',
        },
    ]

    for product in products:
        Subscription.objects.update_or_create(
            name=product['name'],
            defaults=product,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_subscriptions, migrations.RunPython.noop),
    ]
