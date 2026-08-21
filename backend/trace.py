# Trace phone number flow
def _normalise_phone(phone_number):
    phone = phone_number.strip().replace(' ', '').replace('+', '')
    if not phone.startswith('254'):
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        else:
            phone = '254' + phone
    return phone

# Test cases
print("=== Phone Normalization Flow ===")
print()

# Case 1: Correct input
flutter_phone = '0707143297'
normalized = _normalise_phone(flutter_phone)
print(f"1. Flutter sends: {flutter_phone!r}")
print(f"   After _normalise_phone: {normalized!r}")
print(f"   Expected: 254707143297")
print(f"   Match: {normalized == '254707143297'}")
print()

# Case 2: Short number (what appears in logs)
bad_phone = '777'
bad_normalized = _normalise_phone(bad_phone)
print(f"2. If Flutter sends: {bad_phone!r}")
print(f"   After _normalise_phone: {bad_normalized!r}")
print(f"   This is what's appearing in logs: 254777")
print()

# Case 3: Without 0 prefix
no_zero = '707143297'
no_zero_normalized = _normalise_phone(no_zero)
print(f"3. If Flutter sends: {no_zero!r}")
print(f"   After _normalise_phone: {no_zero_normalized!r}")
print()

# Case 4: With 254 prefix
with_prefix = '254707143297'
with_prefix_normalized = _normalise_phone(with_prefix)
print(f"4. If Flutter sends: {with_prefix!r}")
print(f"   After _normalise_phone: {with_prefix_normalized!r}")
print()

print("=== Analysis ===")
print(f"   The logs show '254777' which means the input was '777'")
print(f"   Or the controller value is '777', not '0707143297'")
print(f"   The _normalise_phone function is CORRECT")
print(f"   Fix needed: Ensure Flutter sends '0707143297', not '777'")