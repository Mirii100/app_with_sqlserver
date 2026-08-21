import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection
from accounts.models import CreditCard, DebitCard

# Confirm reflected in DB
c = connection.cursor()
c.execute("SELECT COUNT(*) FROM accounts_creditcard")
print("CreditCard rows in DB:", c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM accounts_debitcard")
print("DebitCard rows in DB:", c.fetchone()[0])

# Show them
print("\nCredit cards (test):")
for cc in CreditCard.objects.all():
    print(f"  {cc.card_type:12} {cc.mask_card_number()} name={cc.cardholder_name} status={cc.status}")
print("\nDebit cards (test):")
for dc in DebitCard.objects.all():
    print(f"  {dc.card_type:12} {dc.mask_card_number()} name={dc.cardholder_name} status={dc.status}")

# Cleanup test cards
n_cc = CreditCard.objects.count()
n_dc = DebitCard.objects.count()
CreditCard.objects.all().delete()
DebitCard.objects.all().delete()
print(f"\nCleaned up {n_cc} credit cards and {n_dc} debit cards.")

c.execute("SELECT COUNT(*) FROM accounts_creditcard")
print("CreditCard rows after cleanup:", c.fetchone()[0])
c.execute("SELECT COUNT(*) FROM accounts_debitcard")
print("DebitCard rows after cleanup:", c.fetchone()[0])
c.close()
