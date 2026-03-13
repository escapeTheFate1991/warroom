"""Phone number validation — reject fake/placeholder numbers."""

import re


# Known junk phone numbers from website builders, hosting providers, etc.
KNOWN_JUNK_NUMBERS = {
    "8005551212",  # 411 directory
    "8004684253",  # GoDaddy support
    "8009291040",  # GoDaddy
    "8882118067",  # Wix support
    "8557019703",  # Squarespace support
    "8883194171",  # WordPress.com
    "8003237751",  # Namecheap
    "8776002011",  # Google My Business
    "8009161575",  # AT&T
    "8008291040",  # GoDaddy alt
    "0000000000",
    "1111111111",
    "1234567890",
}

# Area codes that are typically not real local business lines
SUSPICIOUS_AREA_CODES = {
    "900",  # Premium rate
    "976",  # Premium rate
}


def is_fake_phone(phone: str) -> bool:
    """Return True if phone number looks fake/placeholder."""
    if not phone:
        return True

    digits = re.sub(r'\D', '', phone)

    # Strip leading country code
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    # Too short to be real
    if len(digits) < 10:
        return True

    # Check known junk numbers
    if digits in KNOWN_JUNK_NUMBERS:
        return True

    # All same digit (1111111111, 2222222222, etc.)
    if len(set(digits)) == 1:
        return True

    # Only 2 unique digits — likely junk (1010101010, 1212121212, etc.)
    if len(digits) >= 10 and len(set(digits)) <= 2:
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
        if digits[3:6] == '555' and digits[6:8] == '01':
            return True

    # Suspicious area codes
    if len(digits) >= 10 and digits[:3] in SUSPICIOUS_AREA_CODES:
        return True

    # Area code 000 — not valid
    if len(digits) >= 10 and digits[:3] == '000':
        return True

    return False


def clean_phone(phone: str) -> str:
    """Return phone if valid, empty string if fake."""
    if is_fake_phone(phone):
        return ""
    return phone
