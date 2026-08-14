import random
import string

from django.db import migrations, models


def generate_biller_account_number():
    return '4' + ''.join(random.choices(string.digits, k=11))


def populate_biller_account_numbers(apps, schema_editor):
    Biller = apps.get_model('accounts', 'Biller')
    db_alias = schema_editor.connection.alias
    existing = set(
        Biller.objects.using(db_alias)
        .values_list('account_number', flat=True)
        .exclude(account_number=None)
        .exclude(account_number='')
    )
    for biller in Biller.objects.using(db_alias).all():
        if biller.account_number:
            continue
        number = generate_biller_account_number()
        while number in existing:
            number = generate_biller_account_number()
        existing.add(number)
        biller.account_number = number
        biller.save(update_fields=['account_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_beneficiary'),
    ]

    operations = [
        migrations.AddField(
            model_name='biller',
            name='balance',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Amount paid to this biller's account",
                max_digits=15,
            ),
        ),
        migrations.RunPython(
            populate_biller_account_numbers,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='biller',
            name='account_number',
            field=models.CharField(
                blank=True,
                default='',
                help_text='System-generated unique account number for this biller',
                max_length=50,
                unique=True,
            ),
        ),
    ]
