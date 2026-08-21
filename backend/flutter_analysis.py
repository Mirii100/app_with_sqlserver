import re

with open(r'AlexiaFinancials\lib\screens\home\send_money_screen.dart') as f:
    content = f.read()

# Find the controller initialization
pattern = r'_mpesaNumberController.*?TextEditingController\(\)'
matches = re.findall(pattern, content)
print("_mpesaNumberController initialization:")
for m in matches[:3]:
    print(f"  {m[:80]}...")

# Find the initial value
pattern2 = r'initialPhone'
matches2 = re.findall(pattern2, content[:500])
print(f"\ninitialPhone references: {matches2}")

# Check the _mpesaNumberController usage
pattern3 = r'_mpesaNumberController\.text'
matches3 = re.findall(pattern3, content[:1000])
print(f"\n_mpesaNumberController.text usages: {len(matches3)}")
for m in matches3[:5]:
    print(f"  {m}")