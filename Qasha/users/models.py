from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended User model for Qasha platform"""

    ACCOUNT_TIERS = [
        ('free', 'Free'),
        ('premium', 'Premium (validated)'),
    ]

    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_host = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    account_tier = models.CharField(max_length=20, choices=ACCOUNT_TIERS, default='free')
    premium_since = models.DateTimeField(null=True, blank=True)
    premium_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='User asked to validate a paid Premium account.',
    )

    HOST_VERIFICATION_STATUSES = [
        ('none', 'None'),
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    HOST_VERIFICATION_TIERS = [
        ('', 'None'),
        ('landlord', 'Landlord'),
        ('agency', 'Agency'),
    ]
    host_verification_tier = models.CharField(
        max_length=20,
        choices=HOST_VERIFICATION_TIERS,
        blank=True,
        default='',
    )
    host_verification_status = models.CharField(
        max_length=20,
        choices=HOST_VERIFICATION_STATUSES,
        default='none',
    )
    host_verification_since = models.DateTimeField(null=True, blank=True)
    host_verification_requested_at = models.DateTimeField(null=True, blank=True)
    host_verification_requested_tier = models.CharField(max_length=20, blank=True)

    terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the user accepted Terms and Privacy at registration.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_premium_account(self):
        return self.account_tier == 'premium'

    def has_host_verification_badge(self):
        return (
            self.host_verification_status == 'approved'
            and self.host_verification_tier in ('landlord', 'agency')
        )

    def host_verification_badge_label(self):
        if not self.has_host_verification_badge():
            return ''
        if self.host_verification_tier == 'agency':
            return 'Verified Agency'
        return 'Verified Landlord'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """Additional profile information for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    home_address = models.CharField(max_length=200, blank=True)
    home_suburb = models.CharField(max_length=100, blank=True)
    home_city = models.CharField(max_length=100, blank=True)
    home_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    home_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    search_radius_km = models.PositiveSmallIntegerField(
        default=5,
        help_text='Default GPS search radius on browse (2–200 km, or all South Africa).',
    )
    widen_search_if_empty = models.BooleanField(
        default=True,
        help_text='If no listings in radius, expand search up to 200 km.',
    )
    date_of_birth = models.DateField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

    def area_label(self):
        if self.home_suburb and self.home_city:
            return f'{self.home_suburb}, {self.home_city}'
        return self.location or self.home_city or self.home_suburb or ''

    def has_home_location(self):
        return self.home_latitude is not None and self.home_longitude is not None

    def needs_location_setup(self):
        """True when the user has not saved a home area yet."""
        if (self.home_address or '').strip():
            return False
        if self.has_home_location():
            return False
        return not bool(self.area_label().strip())