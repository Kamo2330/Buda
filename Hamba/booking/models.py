from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CurrencyField(models.CharField):
    """Simple currency code field (e.g. ZAR, USD)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 3)
        super().__init__(*args, **kwargs)


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    reference = models.CharField(
        max_length=20,
        unique=True,
        help_text="Public booking reference shown to customer (e.g. HAM12345).",
    )

    currency = CurrencyField(default="ZAR")
    total_base_fare = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    total_taxes = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    total_extras = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    contact_email = models.EmailField(help_text="Primary email for sending tickets.")
    contact_phone = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    source = models.CharField(
        max_length=50, blank=True, help_text="Source of booking (web, agent, etc.)."
    )
    internal_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.reference} ({self.status})"


class Traveler(models.Model):
    booking = models.ForeignKey(
        Booking, related_name="travelers", on_delete=models.CASCADE
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    date_of_birth = models.DateField(null=True, blank=True)
    document_number = models.CharField(
        max_length=50, blank=True, help_text="ID / passport number"
    )
    nationality = models.CharField(max_length=50, blank=True)

    is_primary_contact = models.BooleanField(default=False)

    special_requests = models.TextField(blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.booking.reference})"


class Payer(models.Model):
    booking = models.OneToOneField(
        Booking, related_name="payer", on_delete=models.CASCADE
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)

    billing_address_line1 = models.CharField(max_length=100, blank=True)
    billing_address_line2 = models.CharField(max_length=100, blank=True)
    billing_city = models.CharField(max_length=50, blank=True)
    billing_postcode = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} [{self.booking.reference}]"


class ExtraType(models.TextChoices):
    WHATSAPP_TICKET = "WHATSAPP_TICKET", "Get ticket via WhatsApp"
    SMS_TICKET = "SMS_TICKET", "Get ticket via SMS"
    REFUND_INSURANCE = (
        "REFUND_INSURANCE",
        "Full refund insurance (illness/death/hospitalisation)",
    )
    DATE_CHANGE_OPTION = (
        "DATE_CHANGE_OPTION",
        "One date change without airline penalty",
    )


class BookingExtra(models.Model):
    booking = models.ForeignKey(
        Booking, related_name="extras", on_delete=models.CASCADE
    )

    extra_type = models.CharField(max_length=50, choices=ExtraType.choices)
    description = models.CharField(
        max_length=255,
        help_text="User-facing description at time of booking (snapshot).",
    )

    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    currency = CurrencyField(default="ZAR")

    applies_to_all_travelers = models.BooleanField(
        default=True,
        help_text="If false, use `applies_to_travelers` to specify travelers.",
    )
    applies_to_travelers = models.ManyToManyField(
        Traveler, related_name="extras", blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.get_extra_type_display()} ({self.price} {self.currency})"


class FlightSegment(models.Model):
    booking = models.ForeignKey(
        Booking, related_name="flight_segments", on_delete=models.CASCADE
    )

    airline_name = models.CharField(max_length=100)
    flight_number = models.CharField(max_length=20)

    origin_airport_code = models.CharField(max_length=10)
    origin_airport_name = models.CharField(max_length=100, blank=True)
    destination_airport_code = models.CharField(max_length=10)
    destination_airport_name = models.CharField(max_length=100, blank=True)

    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField()

    cabin_class = models.CharField(
        max_length=20,
        default="ECONOMY",
        help_text="e.g. economy, premium, business",
    )

    hand_baggage_kg = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Hand baggage allowance in kg.",
    )
    checked_baggage_kg = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Checked baggage allowance in kg.",
    )

    direction = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional: OUTBOUND or RETURN for display purposes.",
    )

    def __str__(self):
        return f"{self.airline_name} {self.flight_number} ({self.origin_airport_code}->{self.destination_airport_code})"


class Payment(models.Model):
    class Method(models.TextChoices):
        CARD = "CARD", "Card"
        EFT = "EFT", "EFT / Bank transfer"
        WALLET = "WALLET", "Mobile wallet"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    booking = models.ForeignKey(
        Booking, related_name="payments", on_delete=models.CASCADE
    )

    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    currency = CurrencyField(default="ZAR")

    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    provider_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Payment gateway reference / transaction id.",
    )
    created_at = models.DateTimeField(default=timezone.now)

    raw_response = models.JSONField(
        null=True, blank=True, help_text="Optional: store gateway response."
    )

    def __str__(self):
        return f"{self.booking.reference} - {self.amount} {self.currency} ({self.status})"


class Airport(models.Model):
    """Airport directory for global autocomplete."""

    iata_code = models.CharField(
        max_length=3,
        unique=True,
        help_text="3-letter IATA code (e.g. JNB, JFK, LHR).",
    )
    name = models.CharField(max_length=255, help_text="Airport name.")
    city = models.CharField(max_length=100, help_text="City or metro area.")
    country = models.CharField(max_length=100, help_text="Country name.")

    is_active = models.BooleanField(
        default=True,
        help_text="Use this to disable closed / inactive airports.",
    )

    class Meta:
        ordering = ["city", "name"]

    def __str__(self):
        return f"{self.city} - {self.name} ({self.iata_code})"
