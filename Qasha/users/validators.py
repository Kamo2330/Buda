"""Profile and signup text rules — block contact sharing in public fields."""

import re

from django.core.exceptions import ValidationError

_CONTACT_PATTERN = re.compile(
    r'(\+?\d[\d\s\-()]{7,}\d|@\w+\.\w+|whatsapp|wa\.me|call\s*me|text\s*me)',
    re.IGNORECASE,
)
_NAME_LETTER = re.compile(r'[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]', re.UNICODE)


def _compact_digits(text: str) -> str:
    return ''.join(c for c in text if c.isdigit())


def validate_platform_phone(value: str) -> str:
    """Phone number stored on the account for Qasha."""
    value = (value or '').strip()
    if not value:
        raise ValidationError('Phone number is required.')

    digits = _compact_digits(value)
    if len(digits) < 9 or len(digits) > 15:
        raise ValidationError('Enter a valid phone number (9–15 digits, e.g. 082 123 4567).')

    return value


def validate_no_peer_contact_in_text(
    value: str,
    *,
    field_label: str = 'This field',
    required: bool = False,
) -> str:
    """Block sharing contact details in text other users may see."""
    value = (value or '').strip()
    if not value:
        if required:
            raise ValidationError(f'{field_label} is required.')
        return value

    if _CONTACT_PATTERN.search(value) or len(_compact_digits(value)) >= 9:
        raise ValidationError(f'{field_label} cannot include a phone number or email address.')

    return value


def validate_person_name(value: str, *, field_label: str = 'Name') -> str:
    """Reject numeric-only names and embedded phone/contact details."""
    value = (value or '').strip()
    if not value:
        return value

    if not _NAME_LETTER.search(value):
        raise ValidationError(f'{field_label} must contain letters.')

    compact = _compact_digits(value)
    if len(compact) >= 6:
        raise ValidationError(f'{field_label} cannot be a phone number.')

    letters_only = re.sub(r'[\s\-\'\.]', '', value)
    if letters_only.isdigit():
        raise ValidationError(f'{field_label} cannot be only numbers.')

    if _CONTACT_PATTERN.search(value):
        raise ValidationError(f'{field_label} cannot include a phone number or email address.')

    return value


def validate_no_contact_in_text(
    value: str,
    *,
    field_label: str = 'This field',
    required: bool = False,
) -> str:
    return validate_no_peer_contact_in_text(
        value,
        field_label=field_label,
        required=required,
    )
