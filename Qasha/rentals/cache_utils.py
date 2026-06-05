"""Short-lived cache for browse filter sidebar (cities, amenity lists)."""

from django.core.cache import cache

from .models import Amenity, Property

FILTER_CACHE_TTL = 300  # 5 minutes


def get_browse_cities():
    key = 'qasha:browse_cities'
    cities = cache.get(key)
    if cities is None:
        cities = list(
            Property.objects.filter(
                is_published=True,
                is_available=True,
                is_occupied=False,
            )
            .values_list('city', flat=True)
            .distinct()
            .order_by('city')
        )
        cache.set(key, cities, FILTER_CACHE_TTL)
    return cities


def get_standard_amenities():
    key = 'qasha:browse_amenities_standard'
    amenities = cache.get(key)
    if amenities is None:
        amenities = list(
            Amenity.objects.filter(is_custom=False).order_by('category', 'name')
        )
        cache.set(key, amenities, FILTER_CACHE_TTL)
    return amenities


def get_host_amenities():
    key = 'qasha:browse_amenities_host'
    amenities = cache.get(key)
    if amenities is None:
        amenities = list(
            Amenity.objects.filter(
                is_custom=True,
                propertyamenity__property__is_published=True,
                propertyamenity__property__is_available=True,
                propertyamenity__property__is_occupied=False,
            )
            .distinct()
            .order_by('name')
        )
        cache.set(key, amenities, FILTER_CACHE_TTL)
    return amenities


def invalidate_browse_cache():
    cache.delete_many([
        'qasha:browse_cities',
        'qasha:browse_amenities_standard',
        'qasha:browse_amenities_host',
    ])
