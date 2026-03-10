"""Phone number validation — reject fake/placeholder numbers."""

import re


def is_fake_phone(phone: str) -> bool:
    """Return True if phone number looks fake/placeholder."""
    if not phone:
        return True

    digits = re.sub(r'\D', '', phone)

    # Too short to be real
    if len(digits) < 7:
        return True

    # All same digit (1111111111, 2222222222, etc.)
    if len(set(digits)) == 1:
        return True

    # Repeating 3-digit pattern (333-333-3333 → 3333333333)
    if len(digits) >= 10:
        first3 = digits[:3]
        if all(d == first3[0] for d in first3) and digits == first3[0] * len(digits):
            return True

    # Sequential ascending (1234567890, 0123456789, etc.)
    asc = ''.join(str(i % 10) for i in range(10))
    doubled_asc = asc + asc
    if len(digits) >= 7 and digits in doubled_asc:
        return True

    # Sequential descending (9876543210, etc.)
    desc = asc[::-1]
    doubled_desc = desc + desc
    if len(digits) >= 7 and digits in doubled_desc:
        return True

    # FCC reserved 555-01XX range (area code + 555-01xx)
    if len(digits) >= 10:
        # Format: XXX-555-01XX
        if digits[3:6] == '555' and digits[6:8] == '01':
            return True
    elif len(digits) == 7:
        # Format: 555-01XX (no area code)
        if digits[:3] == '555' and digits[3:5] == '01':
            return True

    # Common placeholder patterns: 000-000-0000, 999-999-9999
    if len(digits) >= 10 and len(set(digits)) <= 2:
        # Check if it's just two alternating digits like 0101010101
        if all(digits[i] == digits[i % 2] for i in range(len(digits))):
            return True

    return False


def clean_phone(phone: str) -> str:
    """Return phone if valid, empty string if fake."""
    if is_fake_phone(phone):
        return ""
    return phone
