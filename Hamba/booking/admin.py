from django.contrib import admin

from .models import (
    Booking,
    BookingExtra,
    FlightSegment,
    Payer,
    Payment,
    Traveler,
)


class TravelerInline(admin.TabularInline):
    model = Traveler
    extra = 0


class BookingExtraInline(admin.TabularInline):
    model = BookingExtra
    extra = 0


class FlightSegmentInline(admin.TabularInline):
    model = FlightSegment
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "status",
        "total_price",
        "currency",
        "contact_email",
        "created_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("reference", "contact_email", "contact_phone")
    inlines = [TravelerInline, BookingExtraInline, FlightSegmentInline]


@admin.register(Payer)
class PayerAdmin(admin.ModelAdmin):
    list_display = ("booking", "first_name", "last_name", "email", "phone")
    search_fields = ("booking__reference", "email", "first_name", "last_name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "amount",
        "currency",
        "method",
        "status",
        "provider_reference",
        "created_at",
    )
    list_filter = ("method", "status", "currency", "created_at")
    search_fields = ("booking__reference", "provider_reference")


@admin.register(Traveler)
class TravelerAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "booking",
        "is_primary_contact",
    )
    list_filter = ("is_primary_contact",)
    search_fields = ("first_name", "last_name", "booking__reference")


@admin.register(BookingExtra)
class BookingExtraAdmin(admin.ModelAdmin):
    list_display = ("booking", "extra_type", "price", "currency", "created_at")
    list_filter = ("extra_type", "currency", "created_at")
    search_fields = ("booking__reference", "description")


@admin.register(FlightSegment)
class FlightSegmentAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "airline_name",
        "flight_number",
        "origin_airport_code",
        "destination_airport_code",
        "departure_datetime",
        "arrival_datetime",
        "direction",
    )
    list_filter = ("airline_name", "direction")
    search_fields = ("booking__reference", "flight_number")





