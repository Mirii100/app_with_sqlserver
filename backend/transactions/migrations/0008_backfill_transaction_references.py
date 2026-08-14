import random
import string

from django.db import migrations


def generate_reference():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=random.randint(10, 12)))


def backfill_transaction_references(apps, schema_editor):
    Transaction = apps.get_model('transactions', 'Transaction')
    used = set(
        Transaction.objects.exclude(reference__isnull=True)
        .exclude(reference='')
        .values_list('reference', flat=True)
    )
    qs = Transaction.objects.filter(reference__isnull=True) | Transaction.objects.filter(reference='')
    for txn in qs.iterator():
        ref = generate_reference()
        while ref in used:
            ref = generate_reference()
        used.add(ref)
        txn.reference = ref
        txn.save(update_fields=['reference'])


def backfill_goal_transaction_references(apps, schema_editor):
    GoalTransaction = apps.get_model('transactions', 'GoalTransaction')
    used = set(
        GoalTransaction.objects.exclude(reference__isnull=True)
        .exclude(reference='')
        .values_list('reference', flat=True)
    )
    qs = GoalTransaction.objects.filter(reference__isnull=True) | GoalTransaction.objects.filter(reference='')
    for txn in qs.iterator():
        ref = generate_reference()
        while ref in used:
            ref = generate_reference()
        used.add(ref)
        txn.reference = ref
        txn.save(update_fields=['reference'])


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0007_goaltransaction_reference_transaction_reference'),
    ]

    operations = [
        migrations.RunPython(backfill_transaction_references, migrations.RunPython.noop),
        migrations.RunPython(backfill_goal_transaction_references, migrations.RunPython.noop),
    ]
