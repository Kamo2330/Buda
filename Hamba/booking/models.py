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

    # Pricing summary (for the whole booking)
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

    # Meta info (channel, source, notes)
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


def create_sample_booking(reference: str = "HAM12345") -> Booking:
    """
    Convenience helper to create a sample booking that matches the user's example.
    Call from the Django shell:

        from booking.models import create_sample_booking
        booking = create_sample_booking()
    """
    from django.utils import timezone as dj_timezone

    # Prices from your example
    airfare_per_adult = Decimal("1097")
    total_airport_taxes = Decimal("1046")
    # Extras from your example: 27 + 199 + 9 + 339 = 574
    whatsapp_ticket_price = Decimal("27")
    insurance_price = Decimal("199")
    sms_ticket_price = Decimal("9")
    date_change_price = Decimal("339")

    total_extras = (
        whatsapp_ticket_price + insurance_price + sms_ticket_price + date_change_price
    )

    total_price = airfare_per_adult + total_airport_taxes + total_extras

    booking = Booking.objects.create(
        reference=reference,
        currency="ZAR",
        total_base_fare=airfare_per_adult,
        total_taxes=total_airport_taxes,
        total_extras=total_extras,
        total_price=total_price,
        contact_email="guest@example.com",
        contact_phone="0000000000",
        status=Booking.Status.PENDING,
        source="sample_data",
    )

    # One traveler as example
    Traveler.objects.create(
        booking=booking,
        first_name="Sample",
        last_name="Traveler",
        is_primary_contact=True,
    )

    # Extras
    BookingExtra.objects.create(
        booking=booking,
        extra_type=ExtraType.WHATSAPP_TICKET,
        description="Get your ticket via WHATSAPP",
        price=whatsapp_ticket_price,
        currency="ZAR",
    )
    BookingExtra.objects.create(
        booking=booking,
        extra_type=ExtraType.REFUND_INSURANCE,
        description=(
            "Receive a full refund of airfare and taxes in the event "
            "of sudden illness, death or hospitalisation of yourself or "
            "a close relative, prior to departure."
        ),
        price=insurance_price,
        currency="ZAR",
    )
    BookingExtra.objects.create(
        booking=booking,
        extra_type=ExtraType.SMS_TICKET,
        description="Get your ticket via SMS",
        price=sms_ticket_price,
        currency="ZAR",
    )
    BookingExtra.objects.create(
        booking=booking,
        extra_type=ExtraType.DATE_CHANGE_OPTION,
        description=(
            "Make one date change to your flight without paying the "
            "airline penalty fee. You only pay the difference in fare "
            "and taxes if applicable. Valid up to 24 hours prior to "
            "departure of the original ticket."
        ),
        price=date_change_price,
        currency="ZAR",
    )

    # Flight segments based on your example
    # NOTE: Times are approximate examples; adjust as needed.
    dec_20 = dj_timezone.datetime(2025, 12, 20, tzinfo=dj_timezone.get_current_timezone())
    jan_30 = dj_timezone.datetime(2026, 1, 30, tzinfo=dj_timezone.get_current_timezone())

    FlightSegment.objects.create(
        booking=booking,
        airline_name="LIFT",
        flight_number="GE201",
        origin_airport_code="JNB",
        origin_airport_name="Johannesburg, O.R. Tambo International",
        destination_airport_code="DUR",
        destination_airport_name="Durban",
        departure_datetime=dec_20.replace(hour=6, minute=0),
        arrival_datetime=dec_20.replace(hour=7, minute=5),
        cabin_class="ECONOMY",
        hand_baggage_kg=Decimal("7.0"),
        checked_baggage_kg=None,
        direction="OUTBOUND",
    )

    FlightSegment.objects.create(
        booking=booking,
        airline_name="South African Airways",
        flight_number="SA558",
        origin_airport_code="DUR",
        origin_airport_name="Durban",
        destination_airport_code="JNB",
        destination_airport_name="Johannesburg, O.R. Tambo International",
        departure_datetime=jan_30.replace(hour=14, minute=40),
        arrival_datetime=jan_30.replace(hour=15, minute=50),
        cabin_class="ECONOMY",
        hand_baggage_kg=Decimal("7.0"),
        checked_baggage_kg=Decimal("23.0"),
        direction="RETURN",
    )

    # Example payment record (optional)
    Payment.objects.create(
        booking=booking,
        amount=total_price,
        currency="ZAR",
        method=Payment.Method.CARD,
        status=Payment.Status.SUCCESS,
        provider_reference="SAMPLE-TXN-001",
    )

    return booking





