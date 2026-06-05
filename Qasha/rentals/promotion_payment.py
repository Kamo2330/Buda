"""Simulated card payments for featured listings and host verification."""

import uuid

from .promotions import FEATURED_PLANS, VERIFICATION_TIERS, activate_featured_listing, approve_host_verification


def charge_featured_listing(property_obj, plan_key, *, card_last4: str, cardholder_name: str) -> str:
    if plan_key not in FEATURED_PLANS:
        raise ValueError('Invalid featured plan.')

    ref = f'FEAT-{property_obj.pk}-{uuid.uuid4().hex[:8].upper()}'
    activate_featured_listing(property_obj, plan_key)
    return ref


def charge_host_verification(user, tier_key, *, card_last4: str, cardholder_name: str) -> str:
    if tier_key not in VERIFICATION_TIERS:
        raise ValueError('Invalid verification tier.')
    if user.has_host_verification_badge():
        if tier_key == 'agency' and user.host_verification_tier == 'landlord':
            pass
        else:
            raise ValueError('Host verification is already active on your account.')

    ref = f'VER-{user.pk}-{uuid.uuid4().hex[:8].upper()}'
    approve_host_verification(user, tier_key)
    if not user.is_host:
        user.is_host = True
        user.save(update_fields=['is_host', 'updated_at'])
    return ref
