"""Listing limits — verified hosts get full listing perks (photos + video)."""

FREE_MAX_PHOTOS = 5
PREMIUM_MAX_PHOTOS = 25
PREMIUM_MAX_VIDEO_SECONDS = 180
PREMIUM_MAX_VIDEO_BYTES = 150 * 1024 * 1024

FREE_MAX_ACTIVE_LISTINGS = 10
LANDLORD_MAX_ACTIVE_LISTINGS = 30
# Agency: no cap (None)


def get_max_active_listings(user):
    """Max published listings for this host; None means unlimited."""
    if not user.is_authenticated:
        return FREE_MAX_ACTIVE_LISTINGS
    if user.has_host_verification_badge():
        if user.host_verification_tier == 'agency':
            return None
        if user.host_verification_tier == 'landlord':
            return LANDLORD_MAX_ACTIVE_LISTINGS
    if getattr(user, 'account_tier', 'free') == 'premium':
        return LANDLORD_MAX_ACTIVE_LISTINGS
    return FREE_MAX_ACTIVE_LISTINGS


def user_active_listing_count(user):
    return user.properties.filter(is_published=True).count()


def user_can_create_listing(user):
    cap = get_max_active_listings(user)
    if cap is None:
        return True
    return user_active_listing_count(user) < cap


def user_has_full_listing_access(user):
    """Verified hosts (or legacy Premium accounts) unlock more photos and video."""
    if not user.is_authenticated:
        return False
    if getattr(user, 'account_tier', 'free') == 'premium':
        return True
    return user.has_host_verification_badge()


def get_photo_limit(user):
    if user_has_full_listing_access(user):
        return PREMIUM_MAX_PHOTOS
    return FREE_MAX_PHOTOS


def user_can_upload_video(user):
    return user_has_full_listing_access(user)


def validate_video_file(uploaded_file):
    if not uploaded_file:
        return
    if uploaded_file.size > PREMIUM_MAX_VIDEO_BYTES:
        raise ValueError(
            f'Video is too large. Maximum size is {PREMIUM_MAX_VIDEO_BYTES // (1024 * 1024)} MB.'
        )
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        return
    try:
        uploaded_file.seek(0)
        audio = MutagenFile(uploaded_file)
        duration = getattr(audio.info, 'length', None) if audio else None
    except Exception:
        duration = None
    finally:
        uploaded_file.seek(0)
    if duration is not None and duration > PREMIUM_MAX_VIDEO_SECONDS:
        raise ValueError('Video must be 3 minutes or shorter.')


def enforce_listing_media_limits_for_user(user):
    """Trim excess photos and remove video when host loses verified/premium perks."""
    if not user or not user.is_authenticated:
        return
    from rentals.models import Property

    limit = get_photo_limit(user)
    can_video = user_can_upload_video(user)
    for prop in Property.objects.filter(host=user).prefetch_related('images'):
        images = list(prop.images.order_by('-is_primary', 'created_at'))
        for img in images[limit:]:
            if img.image:
                img.image.delete(save=False)
            img.delete()
        if not can_video and prop.video:
            prop.video.delete(save=False)
            prop.video = None
            prop.save(update_fields=['video', 'updated_at'])
