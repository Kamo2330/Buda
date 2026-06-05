from datetime import date, timedelta

from decimal import Decimal

from django.core.exceptions import ValidationError

ACTIVE_TENANT_STATUSES = ('secured', 'accepted')
OPEN_BOOKING_STATUSES = ('pending', 'accepted', 'secured', 'completed')


def uses_qasha_payment(property_obj) -> bool:
    """
    True when booking must use authorize/capture on Qasha.
    Any listing with a securing amount uses Qasha payment even if preference was mis-set.
    """
    if property_obj.payment_preference == "platform":
        return True
    return get_securing_amount(property_obj) > 0


def get_securing_amount(property_obj) -> Decimal:
    """Fixed amount the owner set for tenants to pay on Qasha to secure the space."""
    if property_obj.payment_preference == "direct":
        return Decimal("0")

    amount = property_obj.secure_space_amount or Decimal("0")
    if amount > 0:
        return amount

    # Legacy listings before secure_space_amount existed
    if property_obj.deposit_amount:
        return property_obj.deposit_amount

    return Decimal("0")


def default_check_out(property_obj, check_in):
    if property_obj.lease_type == "short_stay":
        return check_in + timedelta(days=1)
    return check_in + timedelta(days=365)


def dates_overlap(start_a, end_a, start_b, end_b) -> bool:
    """True if two date ranges overlap (inclusive start, exclusive end if end set)."""
    if not start_a or not start_b:
        return False
    end_a = end_a or date.max
    end_b = end_b or date.max
    return start_a <= end_b and start_b <= end_a


def validate_booking_dates(property_obj, check_in, check_out=None, checkout_unknown=False):
    """Shared date rules for BookingForm and platform payment step 2."""
    if not check_in:
        raise ValidationError('Start date is required.')
    if check_in < date.today():
        raise ValidationError('Start date cannot be in the past.')
    if property_obj and property_obj.available_from and check_in < property_obj.available_from:
        raise ValidationError(
            f'This place is available from {property_obj.available_from:%d %b %Y}. '
            f'Choose a start date on or after that day.'
        )
    if property_obj and property_obj.lease_type == 'short_stay' and not check_out:
        raise ValidationError('Please choose a check-out date for a short stay.')
    if (
        property_obj
        and property_obj.lease_type == 'both'
        and not check_out
        and not checkout_unknown
    ):
        raise ValidationError(
            'Please choose a check-out date, or tick that you do not know it yet.'
        )
    if check_in and check_out and check_out <= check_in:
        raise ValidationError('End date must be after the start date.')


def property_has_confirmed_tenant(property_obj) -> bool:
    """True if the listing has an active tenant booking or is marked occupied."""
    from .models import Booking

    if property_obj.is_occupied:
        return True
    return Booking.objects.filter(
        property=property_obj,
        status__in=ACTIVE_TENANT_STATUSES,
    ).exists()


def property_has_active_booking(property_obj) -> bool:
    """True if an accepted or secured tenant booking exists (ignores is_occupied flag)."""
    from .models import Booking

    return Booking.objects.filter(
        property=property_obj,
        status__in=ACTIVE_TENANT_STATUSES,
    ).exists()


def mark_property_occupied(property_obj) -> None:
    property_obj.is_occupied = True
    property_obj.is_available = False
    property_obj.save(update_fields=['is_occupied', 'is_available', 'updated_at'])


def clear_property_occupancy_if_no_tenant(property_obj, except_booking_id=None) -> None:
    """Re-open listing when no other secured or accepted booking holds the place."""
    from .models import Booking

    active = Booking.objects.filter(
        property=property_obj,
        status__in=ACTIVE_TENANT_STATUSES,
    )
    if except_booking_id:
        active = active.exclude(pk=except_booking_id)
    if active.exists():
        return
    property_obj.is_occupied = False
    property_obj.is_available = True
    property_obj.save(update_fields=['is_occupied', 'is_available', 'updated_at'])


def decline_other_pending_bookings(property_obj, except_booking_id) -> int:
    """Decline other pending applications after one is accepted."""
    from .models import Booking
    from .notifications import notify_guest_booking_declined
    from .payment_utils import release_booking_authorization

    declined = 0
    others = Booking.objects.filter(property=property_obj, status='pending').exclude(pk=except_booking_id)
    for booking in others:
        release_booking_authorization(booking)
        booking.status = 'declined'
        booking.save(update_fields=['status', 'updated_at'])
        notify_guest_booking_declined(booking)
        declined += 1
    return declined
