from django.db import migrations


def seed_rewards(apps, schema_editor):
    Reward = apps.get_model('rewards', 'Reward')
    rewards = [
        ('Airtime KSh 50', 'Get KSh 50 of airtime loaded to your phone.', 500, '📱'),
        ('Data bundle 1GB', '1GB mobile data valid for 7 days.', 800, '📶'),
        ('Shopping voucher KSh 200', 'KSh 200 voucher at partner shops.', 1500, '🛍️'),
        ('Cashback KSh 100', 'KSh 100 credited back to your account.', 1200, '💸'),
    ]
    for name, description, points_cost, icon in rewards:
        Reward.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
                'points_cost': points_cost,
                'icon': icon,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('rewards', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_rewards, migrations.RunPython.noop),
    ]
