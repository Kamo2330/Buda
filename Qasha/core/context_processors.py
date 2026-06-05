from django.conf import settings

from .maps_utils import places_autocomplete_enabled


def google_maps(request):
    return {
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'places_autocomplete_enabled': places_autocomplete_enabled(),
    }
