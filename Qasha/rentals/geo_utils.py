"""GPS distance helpers for browse and search ranking."""

from django.db.models import Case, FloatField, IntegerField, Q, Value, When
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.utils import timezone

MIN_RADIUS_KM = 2
DEFAULT_RADIUS_KM = 5
LOCAL_MAX_RADIUS_KM = 15
MAX_RADIUS_KM = 200
NATIONWIDE_RADIUS_KM = 0
DISTANCE_SORT_FALLBACK_KM = 99999.0

RADIUS_FORM_CHOICES = [
    (2, '2 km'),
    (5, '5 km (default)'),
    (10, '10 km'),
    (15, '15 km'),
    (50, '50 km'),
    (100, '100 km'),
    (200, '200 km'),
    (NATIONWIDE_RADIUS_KM, 'All South Africa'),
]

HAVERSINE_KM_SQL = """
(6371.0 * acos(
    min(1.0, max(-1.0,
        cos(radians(%s)) * cos(radians(latitude)) * cos(radians(longitude) - radians(%s))
        + sin(radians(%s)) * sin(radians(latitude))
    ))
))
"""


def is_nationwide_radius(radius_km):
    return radius_km is not None and int(radius_km) == NATIONWIDE_RADIUS_KM


def clamp_radius_km(value, default=DEFAULT_RADIUS_KM):
    try:
        km = int(value)
    except (TypeError, ValueError):
        km = default
    if km == NATIONWIDE_RADIUS_KM:
        return NATIONWIDE_RADIUS_KM
    return max(MIN_RADIUS_KM, min(MAX_RADIUS_KM, km))


def parse_radius_from_request(request, profile=None):
    """Radius from query string, else profile default, else platform default."""
    raw = request.GET.get('radius_km')
    if raw not in (None, ''):
        return clamp_radius_km(raw)
    if profile is not None and profile.search_radius_km is not None:
        return clamp_radius_km(profile.search_radius_km)
    return DEFAULT_RADIUS_KM


def parse_widen_from_request(request, profile=None):
    if 'widen_search' in request.GET:
        return request.GET.get('widen_search') in ('1', 'true', 'on', 'yes')
    if profile is not None:
        return profile.widen_search_if_empty
    return True


def annotate_distance_km(queryset, lat, lng):
    return queryset.annotate(
        distance_km=RawSQL(
            HAVERSINE_KM_SQL,
            (lat, lng, lat),
            output_field=FloatField(),
        ),
    )


def annotate_distance_km_optional(queryset, lat, lng):
    """Distance for geocoded rows; null for listings without map coordinates."""
    haversine = RawSQL(
        HAVERSINE_KM_SQL,
        (lat, lng, lat),
        output_field=FloatField(),
    )
    return queryset.annotate(
        distance_km=Case(
            When(
                Q(latitude__isnull=False) & Q(longitude__isnull=False),
                then=haversine,
            ),
            default=Value(None),
            output_field=FloatField(),
        ),
    )


def get_user_home_coords(user):
    if not user.is_authenticated:
        return None, None
    from users.models import UserProfile
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        return None, None
    if profile.home_latitude is None or profile.home_longitude is None:
        return None, None
    return float(profile.home_latitude), float(profile.home_longitude)


def apply_geo_browse(queryset, request):
    """
    Filter to listings within radius (GPS). Optionally widen up to 200 km if empty.
    Radius 0 = all South Africa (includes listings without map pins; sorted by distance).
    """
    info = {
        'active': False,
        'radius_km': DEFAULT_RADIUS_KM,
        'radius_requested': DEFAULT_RADIUS_KM,
        'widened': False,
        'nationwide': False,
        'area': '',
        'min_km': MIN_RADIUS_KM,
        'max_km': MAX_RADIUS_KM,
        'default_km': DEFAULT_RADIUS_KM,
    }

    lat, lng = get_user_home_coords(request.user)
    if lat is None:
        return {'queryset': queryset, 'info': info}

    profile = request.user.profile
    radius_requested = parse_radius_from_request(request, profile)
    widen = parse_widen_from_request(request, profile)

    if is_nationwide_radius(radius_requested):
        within = annotate_distance_km_optional(queryset, lat, lng)
        effective_radius = NATIONWIDE_RADIUS_KM
        widened = False
        nationwide = True
    else:
        nationwide = False
        full = annotate_distance_km_optional(queryset, lat, lng)
        within = full.filter(
            Q(distance_km__lte=radius_requested) | Q(distance_km__isnull=True)
        )
        effective_radius = radius_requested
        widened = False

        if not full.filter(distance_km__lte=radius_requested).exists() and widen:
            within = full.filter(
                Q(distance_km__lte=MAX_RADIUS_KM) | Q(distance_km__isnull=True)
            )
            effective_radius = MAX_RADIUS_KM
            widened = True

    info.update({
        'active': True,
        'radius_km': effective_radius,
        'radius_requested': radius_requested,
        'widened': widened,
        'nationwide': nationwide,
        'area': profile.area_label(),
        'widen_enabled': widen,
    })
    return {'queryset': within, 'info': info}


def apply_browse_ordering(queryset, request, geo_active=False, nationwide=False):
    """Featured first, then distance (if GPS browse), then user sort."""
    now = timezone.now()
    queryset = queryset.annotate(
        featured_rank=Case(
            When(featured_until__gt=now, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    )

    if geo_active and hasattr(queryset.model, 'latitude'):
        if nationwide:
            queryset = queryset.annotate(
                sort_distance=Coalesce(
                    'distance_km',
                    Value(DISTANCE_SORT_FALLBACK_KM, output_field=FloatField()),
                ),
            )
            order_head = ['-featured_rank', 'sort_distance']
        else:
            queryset = queryset.annotate(
                sort_distance=Coalesce(
                    'distance_km',
                    Value(DISTANCE_SORT_FALLBACK_KM, output_field=FloatField()),
                ),
            )
            order_head = ['-featured_rank', 'sort_distance']
    else:
        order_head = ['-featured_rank']

    sort_by = request.GET.get('sort', 'newest')
    from .query_utils import annotate_listing_price

    if sort_by in ('price_low', 'price_high'):
        queryset = annotate_listing_price(queryset)
    if sort_by == 'newest':
        return queryset.order_by(*order_head, '-created_at')
    if sort_by == 'price_low':
        return queryset.order_by(*order_head, 'listing_price')
    if sort_by == 'price_high':
        return queryset.order_by(*order_head, '-listing_price')
    return queryset.order_by(*order_head, '-created_at')
