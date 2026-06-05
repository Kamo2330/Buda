"""Google Maps / Places configuration helpers."""

from django.conf import settings


def places_autocomplete_enabled() -> bool:
    return bool(str(getattr(settings, 'GOOGLE_MAPS_API_KEY', '')).strip())
