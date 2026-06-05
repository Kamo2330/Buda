from django import template

from rentals.media_utils import stored_media_exists

register = template.Library()


@register.filter
def user_has_profile_photo(user):
    if not user or not getattr(user, 'profile_picture', None):
        return False
    return bool(user.profile_picture.name) and stored_media_exists(user.profile_picture)


@register.filter
def user_profile_photo_url(user):
    if user_has_profile_photo(user):
        return user.profile_picture.url
    return ''
