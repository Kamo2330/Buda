from django.db import models
from django.contrib.auth import get_user_model

from .media_utils import ALLOWED_VIDEO_EXTENSIONS, stored_media_exists
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator

User = get_user_model()


class Property(models.Model):
    """Property model for rental listings"""
    
    PROPERTY_TYPES = [
        ('room', 'Room'),
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('studio', 'Studio'),
        ('office', 'Office space'),
        ('townhouse', 'Townhouse'),
        ('cottage', 'Cottage / flatlet'),
        ('other', 'Other'),
    ]
    
    FURNISHING_TYPES = [
        ('furnished', 'Furnished'),
        ('unfurnished', 'Unfurnished'),
        ('semi_furnished', 'Semi-furnished'),
    ]
    
    LEASE_TYPES = [
        ('monthly', 'Monthly'),
        ('short_stay', 'Short Stay'),
        ('both', 'Both'),
    ]

    PAYMENT_PREFERENCES = [
        ('platform', 'They pay on Qasha'),
        ('direct', 'They pay me (the owner)'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    property_type_custom = models.CharField(
        max_length=80,
        blank=True,
        help_text='When property type is Other, the label shown on the listing.',
    )
    furnishing = models.CharField(max_length=20, choices=FURNISHING_TYPES)
    lease_type = models.CharField(max_length=20, choices=LEASE_TYPES)
    
    # Location
    address = models.CharField(max_length=200)
    suburb = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Pricing
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    secure_space_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Amount a tenant pays on Qasha to secure this space when the host accepts.',
    )
    utilities_included = models.BooleanField(default=False)
    payment_preference = models.CharField(
        max_length=20,
        choices=PAYMENT_PREFERENCES,
        default='platform',
    )
    
    # Property Details
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    area_sqm = models.PositiveIntegerField(blank=True, null=True)
    max_occupants = models.PositiveIntegerField(default=1)
    
    # Availability
    available_from = models.DateField()
    available_until = models.DateField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_occupied = models.BooleanField(
        default=False,
        help_text='Tenant is in the place; listing stays off browse until marked vacant.',
    )
    
    # Host Information
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    
    # Optional video tour (images use PropertyImage)
    video = models.FileField(
        upload_to='properties/videos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=list(ALLOWED_VIDEO_EXTENSIONS))],
    )

    # Status and Verification
    is_verified = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)

    # Paid featured placement (separate from account Premium)
    featured_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Listing appears first in search and on the homepage until this time.',
    )
    featured_plan = models.CharField(max_length=10, blank=True)
    featured_payment_requested_at = models.DateTimeField(null=True, blank=True)
    featured_payment_requested_plan = models.CharField(max_length=10, blank=True)

    listing_terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Host accepted listing declarations and Terms when publishing.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Properties"
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['is_published', 'is_available', 'is_occupied', '-created_at'],
                name='rentals_prop_browse_new',
            ),
            models.Index(
                fields=['is_published', 'is_available', 'is_occupied', 'city'],
                name='rentals_prop_browse_city',
            ),
            models.Index(fields=['-featured_until'], name='rentals_prop_featured'),
            models.Index(fields=['city'], name='rentals_prop_city'),
            models.Index(fields=['suburb'], name='rentals_prop_suburb'),
            models.Index(fields=['host', '-created_at'], name='rentals_prop_host_new'),
        ]
    
    def __str__(self):
        return self.title

    def get_display_image(self):
        """Photo shown on the timeline (primary with a file on disk, else first available)."""
        available = self.get_available_images()
        for img in available:
            if img.is_primary:
                return img
        return available[0] if available else None

    def get_available_images(self):
        """Property images whose files are present in storage (newest primary order)."""
        cache = getattr(self, '_prefetched_objects_cache', {})
        images = cache.get('images')
        if images is not None:
            ordered = sorted(images, key=lambda i: (not i.is_primary, i.created_at))
            return [img for img in ordered if img.has_file()]
        return [
            img
            for img in self.images.order_by('-is_primary', 'created_at')
            if img.has_file()
        ]

    def has_video_file(self):
        return bool(self.video) and stored_media_exists(self.video)

    def is_featured_active(self):
        from django.utils import timezone
        return bool(self.featured_until and self.featured_until > timezone.now())

    def get_listing_property_type_label(self):
        if self.property_type == 'other' and self.property_type_custom:
            return self.property_type_custom
        return self.get_property_type_display()


class PropertyImage(models.Model):
    """Images for properties"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='properties/')
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def has_file(self):
        return stored_media_exists(self.image)
    
    class Meta:
        indexes = [
            models.Index(
                fields=['property', '-is_primary', 'created_at'],
                name='rentals_pimg_display',
            ),
        ]

    def __str__(self):
        return f"{self.property.title} - Image {self.id}"


class Amenity(models.Model):
    """Amenities available in properties"""
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)  # For icon class names
    category = models.CharField(max_length=50, blank=True)
    is_custom = models.BooleanField(
        default=False,
        help_text='Added by a host on the listing form (not in the standard filter list).',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='amenities_created',
    )

    class Meta:
        verbose_name_plural = "Amenities"
        indexes = [
            models.Index(fields=['is_custom', 'name'], name='rentals_amenity_custom'),
        ]
    
    def __str__(self):
        return self.name


class PropertyAmenity(models.Model):
    """Many-to-many relationship between properties and amenities"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_amenities')
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['property', 'amenity']
        verbose_name_plural = "Property Amenities"
        indexes = [
            models.Index(fields=['amenity'], name='rentals_pamenity_amenity'),
        ]


class PropertyRule(models.Model):
    """Rules for properties"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rules')
    rule_text = models.CharField(max_length=200)
    is_important = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.property.title} - {self.rule_text}"


class Booking(models.Model):
    """Booking model for rental reservations"""
    
    STATUS_CHOICES = [
        ('pending', 'Booking request — awaiting owner'),
        ('accepted', 'Accepted — arrange payment with host'),
        ('secured', 'Confirmed — payment captured'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    PAYMENT_AUTH_STATUS = [
        ('none', 'No authorization'),
        ('authorized', 'Authorized (hold — not charged yet)'),
        ('captured', 'Captured (paid)'),
        ('released', 'Authorization released'),
    ]
    
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    check_in_date = models.DateField()
    check_out_date = models.DateField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    special_requests = models.TextField(blank=True)
    host_note = models.TextField(blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    payment_on_file = models.BooleanField(
        default=False,
        help_text='Tenant submitted card details at application; charged when host accepts.',
    )
    payment_cardholder_name = models.CharField(max_length=120, blank=True)
    payment_card_last4 = models.CharField(max_length=4, blank=True)
    payment_auth_status = models.CharField(
        max_length=20,
        choices=PAYMENT_AUTH_STATUS,
        default='none',
    )
    authorization_ref = models.CharField(max_length=40, blank=True)
    authorized_at = models.DateTimeField(blank=True, null=True)
    released_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['property', 'status'], name='rentals_booking_host'),
            models.Index(fields=['guest', 'status'], name='rentals_booking_guest'),
        ]

    def __str__(self):
        return f"{self.guest.username} - {self.property.title}"
    
    def duration_days(self):
        if not self.check_out_date:
            return None
        return (self.check_out_date - self.check_in_date).days

    def is_payment_authorized(self):
        return self.payment_auth_status == 'authorized'

    def is_payment_captured(self):
        return self.payment_auth_status == 'captured'

    def uses_qasha_payment(self):
        from .booking_utils import uses_qasha_payment as _uses_qasha

        return _uses_qasha(self.property)

    def is_paid_on_qasha(self):
        return self.status == 'secured' or self.payment_auth_status == 'captured'


class Message(models.Model):
    """Messages between users"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='messages', blank=True, null=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read'], name='rentals_msg_unread'),
            models.Index(fields=['recipient', '-created_at'], name='rentals_msg_inbox'),
            models.Index(fields=['sender', '-created_at'], name='rentals_msg_sent'),
        ]
    
    def __str__(self):
        return f"{self.sender.username} to {self.recipient.username}: {self.subject}"

    def save(self, *args, **kwargs):
        from django.utils import timezone

        if not self.pk and not self.delivered_at:
            self.delivered_at = timezone.now()
        if self.read_at and not self.is_read:
            self.is_read = True
        elif self.is_read and not self.read_at:
            self.read_at = timezone.now()
        super().save(*args, **kwargs)

    def status_for_sender(self):
        """Sent → delivered → seen (read by recipient)."""
        if self.read_at:
            return 'seen'
        if self.delivered_at:
            return 'delivered'
        return 'sent'


class Review(models.Model):
    """Private tenant feedback — visible to host and platform staff only."""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['property', 'reviewer']
        verbose_name = 'Private feedback'
        verbose_name_plural = 'Private feedback'
    
    def __str__(self):
        return f"Feedback from {self.reviewer.username} on {self.property.title}"


class Wishlist(models.Model):
    """User wishlist for properties"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'property']
        indexes = [
            models.Index(fields=['user'], name='rentals_wishlist_user'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.property.title}"