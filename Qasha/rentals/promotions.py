"""Featured listings and host verification pricing (ZAR)."""

from datetime import timedelta

from django.utils import timezone

from users.premium_payment import activate_premium_account
from users.tiers import FREE_MAX_PHOTOS, enforce_listing_media_limits_for_user

FEATURED_PLANS = {
    '7d': {'days': 7, 'price_zar': 29, 'label': '7 days'},
    '30d': {'days': 30, 'price_zar': 100, 'label': '30 days'},
}

VERIFICATION_TIERS = {
    'landlord': {
        'price_zar': 49,
        'label': 'Verified Landlord',
        'badge': 'Verified Landlord',
        'max_listings': 30,
        'perks': [
            'Verified badge on profile and listings',
            'Up to 25 photos per listing',
            '1 video per listing',
            'Up to 30 active listings',
        ],
    },
    'agency': {
        'price_zar': 199,
        'label': 'Verified Agency',
        'badge': 'Verified Agency',
        'max_listings': None,
        'perks': [
            'Verified badge on profile and listings',
            'Agency profile',
            'Company logo displayed',
            'Up to 25 photos and 1 video per listing',
            'Unlimited active listings',
            'Priority listing approval',
            'Discount on featured listings',
        ],
    },
}

FREE_ACCOUNT_PLAN = {
    'label': 'Unverified User (Free)',
    'price_zar': 0,
    'max_listings': 10,
    'perks': [
        'Up to 10 active listings',
        f'Up to {FREE_MAX_PHOTOS} photos per listing',
        'Basic profile',
        'Standard support',
    ],
}

FEATURED_LISTING_HELP = (
    'Featured listings appear first in browse — not random. With your home on the map, '
    'results are sorted by GPS distance (default 5 km; you can choose up to 200 km or '
    'All South Africa). Featured paid listings still rank above others in your results. '
    'The homepage also has a Featured row for highlighted placements.'
)


def activate_featured_listing(property_obj, plan_key):
    """Extend or start featured period after admin confirms payment."""
    plan = FEATURED_PLANS[plan_key]
    now = timezone.now()
    if property_obj.featured_until and property_obj.featured_until > now:
        start = property_obj.featured_until
    else:
        start = now
    property_obj.featured_until = start + timedelta(days=plan['days'])
    property_obj.featured_plan = plan_key
    property_obj.featured_payment_requested_at = None
    property_obj.featured_payment_requested_plan = ''
    property_obj.save(
        update_fields=[
            'featured_until',
            'featured_plan',
            'featured_payment_requested_at',
            'featured_payment_requested_plan',
            'updated_at',
        ]
    )


def approve_host_verification(user, tier_key):
    """Mark host verification active after admin confirms payment and documents."""
    user.host_verification_tier = tier_key
    user.host_verification_status = 'approved'
    user.host_verification_since = timezone.now()
    user.host_verification_requested_at = None
    user.host_verification_requested_tier = ''
    activate_premium_account(user, commit=False)
    user.save(
        update_fields=[
            'host_verification_tier',
            'host_verification_status',
            'host_verification_since',
            'host_verification_requested_at',
            'host_verification_requested_tier',
            'account_tier',
            'premium_since',
            'premium_requested_at',
            'updated_at',
        ]
    )


def grant_host_verification(user, tier_key):
    """Free gift — approve verification without a payment request."""
    approve_host_verification(user, tier_key)


def reject_host_verification(user):
    """Decline a pending verification request and remove perks granted only via verification."""
    user.host_verification_status = 'rejected'
    user.host_verification_requested_at = None
    user.host_verification_requested_tier = ''
    if not user.has_host_verification_badge() and user.account_tier == 'premium':
        user.account_tier = 'free'
        user.premium_since = None
        user.premium_requested_at = None
    user.save(
        update_fields=[
            'host_verification_status',
            'host_verification_requested_at',
            'host_verification_requested_tier',
            'account_tier',
            'premium_since',
            'premium_requested_at',
            'updated_at',
        ]
    )
    enforce_listing_media_limits_for_user(user)


def revoke_host_verification(user):
    """Remove verification badge and listing perks."""
    user.host_verification_tier = ''
    user.host_verification_status = 'none'
    user.host_verification_since = None
    user.host_verification_requested_at = None
    user.host_verification_requested_tier = ''
    if user.account_tier == 'premium':
        user.account_tier = 'free'
        user.premium_since = None
    user.save(
        update_fields=[
            'host_verification_tier',
            'host_verification_status',
            'host_verification_since',
            'host_verification_requested_at',
            'host_verification_requested_tier',
            'account_tier',
            'premium_since',
            'updated_at',
        ]
    )
    enforce_listing_media_limits_for_user(user)


def gift_featured_for_host(user, plan_key='7d'):
    """Free featured placement on every listing owned by this host."""
    if plan_key not in FEATURED_PLANS:
        plan_key = '7d'
    count = 0
    for prop in user.properties.all():
        activate_featured_listing(prop, plan_key)
        count += 1
    return count
