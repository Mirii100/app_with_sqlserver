def _normalise_phone(phone_number):
    phone = phone_number.strip().replace(' ', '').replace('+', '')
    if not phone.startswith('254'):
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        else:
            phone = '254' + phone
    return phone

phone = '0707143297'
result = _normalise_phone(phone)
expected = '254707143297'
print(f'Input:  {phone!r}')
print(f'Output: {result!r}')
print(f'Expected: {expected!r}')
print(f'Match: {result == expected}')