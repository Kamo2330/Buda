"""Shared queryset tuning for browse and detail pages."""

from django.db.models import Case, DecimalField, F, Prefetch, When
from django.db.models.functions import Coalesce

from .models import Property, PropertyImage

IMAGE_PREFETCH = Prefetch(
    'images',
    queryset=PropertyImage.objects.order_by('-is_primary', 'created_at'),
)


def annotate_listing_price(queryset):
    """Single comparable price for monthly, short-stay, and both-type listings."""
    return queryset.annotate(
        listing_price=Case(
            When(lease_type='short_stay', then=F('nightly_rate')),
            When(lease_type='monthly', then=F('monthly_rent')),
            When(lease_type='both', then=Coalesce(F('monthly_rent'), F('nightly_rate'))),
            default=F('monthly_rent'),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )


def property_listing_queryset(base=None):
    """select_related + prefetch to avoid N+1 on feed and detail pages."""
    qs = base if base is not None else Property.objects.all()
    return qs.select_related('host').prefetch_related(
        IMAGE_PREFETCH,
        'property_amenities__amenity',
    )
