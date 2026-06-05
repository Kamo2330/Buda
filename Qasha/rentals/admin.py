from django.contrib import admin
from django.utils import timezone

from .promotions import activate_featured_listing, FEATURED_PLANS
from .models import (
    Property, PropertyImage, Amenity, PropertyAmenity,
    PropertyRule, Booking, Message, Review, Wishlist
)


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


class PropertyAmenityInline(admin.TabularInline):
    model = PropertyAmenity
    extra = 1


class PropertyRuleInline(admin.TabularInline):
    model = PropertyRule
    extra = 1


class FeaturedFilter(admin.SimpleListFilter):
    title = 'Featured status'
    parameter_name = 'featured'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Currently featured'),
            ('none', 'Not featured'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'active':
            return queryset.filter(featured_until__gt=now)
        if self.value() == 'none':
            return queryset.filter(featured_until__isnull=True) | queryset.filter(featured_until__lte=now)
        return queryset


@admin.action(description='🎁 FREE featured 7 days (query / promotion)')
def activate_featured_plan_7d(modeladmin, request, queryset):
    for prop in queryset:
        activate_featured_listing(prop, '7d')


@admin.action(description='🎁 FREE featured 30 days (query / promotion)')
def activate_featured_plan_30d(modeladmin, request, queryset):
    for prop in queryset:
        activate_featured_listing(prop, '30d')


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'host',
        'city',
        'monthly_rent',
        'featured_status',
        'is_published',
        'featured_until',
    )
    list_filter = (
        FeaturedFilter,
        'city',
        'is_published',
        'is_available',
        'property_type',
    )
    search_fields = ('title', 'address', 'city', 'suburb', 'host__username', 'host__email')
    list_editable = ('is_published',)
    actions = [activate_featured_plan_7d, activate_featured_plan_30d]
    inlines = [PropertyImageInline, PropertyAmenityInline, PropertyRuleInline]
    autocomplete_fields = ('host',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'property_type', 'property_type_custom', 'furnishing', 'lease_type')
        }),
        ('Location', {
            'fields': ('address', 'suburb', 'city', 'latitude', 'longitude')
        }),
        ('Pricing', {
            'fields': (
                'monthly_rent', 'nightly_rate', 'secure_space_amount',
                'deposit_amount', 'utilities_included', 'payment_preference',
            )
        }),
        ('Media', {'fields': ('video',)}),
        ('Property Details', {
            'fields': ('bedrooms', 'bathrooms', 'area_sqm', 'max_occupants')
        }),
        ('Availability', {
            'fields': ('available_from', 'available_until', 'is_available', 'is_occupied')
        }),
        ('Host & Status', {
            'fields': ('host', 'is_verified', 'is_published')
        }),
        ('Featured listing (free gifts for queries)', {
            'description': 'Use list actions above for one-click free featured placement, or set featured_until manually.',
            'fields': (
                'featured_until',
                'featured_plan',
                'featured_payment_requested_at',
                'featured_payment_requested_plan',
            ),
        }),
    )

    @admin.display(description='Featured')
    def featured_status(self, obj):
        if obj.is_featured_active():
            return f'Yes until {obj.featured_until:%d %b %Y}'
        return '—'


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'is_primary', 'caption', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('property__title', 'caption')


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'icon', 'is_custom', 'created_by')
    list_filter = ('category', 'is_custom')
    search_fields = ('name', 'category')


@admin.register(PropertyAmenity)
class PropertyAmenityAdmin(admin.ModelAdmin):
    list_display = ('property', 'amenity')
    list_filter = ('amenity__category',)
    search_fields = ('property__title', 'amenity__name')


@admin.register(PropertyRule)
class PropertyRuleAdmin(admin.ModelAdmin):
    list_display = ('property', 'rule_text', 'is_important')
    list_filter = ('is_important',)
    search_fields = ('property__title', 'rule_text')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'property', 'guest', 'check_in_date', 'check_out_date', 'total_amount',
        'status', 'payment_auth_status', 'created_at',
    )
    list_filter = ('status', 'check_in_date', 'created_at')
    search_fields = ('property__title', 'guest__username', 'guest__email')
    list_editable = ('status',)
    date_hierarchy = 'check_in_date'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'property', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'subject', 'message')
    list_editable = ('is_read',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('property', 'reviewer', 'rating', 'is_public', 'created_at')
    list_filter = ('rating', 'is_public', 'created_at')
    search_fields = ('property__title', 'reviewer__username', 'comment')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'property__title')
