"""Simulated on-platform charge for Account Premium (demo — replace with PayFast/Stripe)."""

import uuid

from django.utils import timezone


def activate_premium_account(user, *, commit: bool = True) -> None:
    """Grant listing perks tier (used after verification or standalone premium pay)."""
    now = timezone.now()
    user.account_tier = 'premium'
    user.premium_since = now
    user.premium_requested_at = None
    if commit:
        user.save(
            update_fields=[
                'account_tier',
                'premium_since',
                'premium_requested_at',
                'updated_at',
            ]
        )


def charge_premium_account(user, *, card_last4: str, cardholder_name: str) -> str:
    """
    Capture Premium payment immediately and upgrade the account.
    Returns a payment reference for receipts/logs.
    """
    if user.is_premium_account:
        raise ValueError('Account is already Premium.')

    ref = f'PREM-{user.pk}-{uuid.uuid4().hex[:8].upper()}'
    activate_premium_account(user)
    return ref
