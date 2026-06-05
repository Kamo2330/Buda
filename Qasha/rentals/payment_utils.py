"""Simulated payment authorization, capture, and release (Qasha demo)."""

import uuid

from django.utils import timezone

from .models import Booking


def _auth_reference(booking: Booking) -> str:
    return f"AUTH-{booking.pk or 'new'}-{uuid.uuid4().hex[:8].upper()}"


def authorize_booking_payment(booking: Booking) -> None:
    """
    Step 2: Hold funds on the card — authorization only, not a full charge.
    Real providers: Stripe PaymentIntent with capture_method=manual, etc.
    """
    if not booking.payment_on_file:
        raise ValueError("No payment method on file.")

    now = timezone.now()
    booking.payment_auth_status = "authorized"
    booking.authorization_ref = booking.authorization_ref or _auth_reference(booking)
    booking.authorized_at = now
    booking.released_at = None
    booking.save(
        update_fields=[
            "payment_auth_status",
            "authorization_ref",
            "authorized_at",
            "released_at",
            "updated_at",
        ]
    )


def capture_booking_payment(booking: Booking) -> None:
    """
    Step 4A: Owner accepted — capture the authorized amount and confirm booking.
    """
    if booking.payment_auth_status != "authorized":
        raise ValueError("No active payment authorization to capture.")

    now = timezone.now()
    booking.payment_auth_status = "captured"
    booking.status = "secured"
    booking.paid_at = now
    booking.save(update_fields=["payment_auth_status", "status", "paid_at", "updated_at"])

    prop = booking.property
    prop.is_occupied = True
    prop.is_available = False
    prop.save(update_fields=["is_occupied", "is_available", "updated_at"])


def release_booking_authorization(booking: Booking) -> None:
    """
    Step 4B / cancel: Release hold — tenant was never fully charged.
    """
    if booking.payment_auth_status != "authorized":
        return

    booking.payment_auth_status = "released"
    booking.released_at = timezone.now()
    booking.save(update_fields=["payment_auth_status", "released_at", "updated_at"])


# Backwards-compatible alias used by views
def charge_booking_on_accept(booking: Booking) -> None:
    capture_booking_payment(booking)
