def profile_location(request):
    if not request.user.is_authenticated:
        return {'needs_home_location': False}
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        return {'needs_home_location': True}
    return {'needs_home_location': profile.needs_location_setup()}
