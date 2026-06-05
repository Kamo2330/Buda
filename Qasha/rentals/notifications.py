"""In-app notifications to guests when booking status changes."""

from .models import Booking, Message


def _booking_message_subject(booking: Booking) -> str:
    return f"Booking update: {booking.property.title}"


def _format_zar(amount) -> str:
    if amount is None:
        return "R 0"
    val = float(amount)
    if val == int(val):
        return f"R {int(val):,}"
    return f"R {val:,.2f}"


def _create_guest_notification(booking: Booking, body: str) -> None:
    host = booking.property.host
    Message.objects.create(
        sender=host,
        recipient=booking.guest,
        property=booking.property,
        subject=_booking_message_subject(booking),
        message=body.strip(),
        is_read=False,
    )


def notify_guest_booking_accepted(booking: Booking) -> None:
    """Tell the tenant their request was accepted (and if payment was captured)."""
    booking.refresh_from_db()
    host_name = booking.property.host.get_full_name() or booking.property.host.username
    prop_title = booking.property.title
    amount_text = _format_zar(booking.total_amount)

    if booking.is_paid_on_qasha():
        body = (
            f"Good news — {host_name} accepted your booking request for \"{prop_title}\".\n\n"
            f"Payment of {amount_text} has been captured on Qasha. "
            f"Your booking is confirmed.\n\n"
            f"Open Manage → Applications to see the details, or reply here if you have questions."
        )
    elif booking.status == "accepted":
        body = (
            f"{host_name} accepted your booking request for \"{prop_title}\".\n\n"
            f"Arrange payment with them using Messages on Qasha."
        )
    else:
        body = (
            f"{host_name} accepted your booking request for \"{prop_title}\".\n\n"
            f"Check Manage → Applications for the latest status."
        )
    _create_guest_notification(booking, body)


def notify_guest_booking_declined(booking: Booking) -> None:
    booking.refresh_from_db()
    host_name = booking.property.host.get_full_name() or booking.property.host.username
    prop_title = booking.property.title
    released = booking.payment_auth_status == "released"
    extra = (
        " Any hold on your card has been released — you were not charged."
        if released
        else ""
    )
    body = (
        f"{host_name} declined your booking request for \"{prop_title}\".{extra}\n\n"
        f"You can browse other places on the home timeline."
    )
    _create_guest_notification(booking, body)


def notify_guest_booking_cancelled_by_host(booking: Booking) -> None:
    booking.refresh_from_db()
    host_name = booking.property.host.get_full_name() or booking.property.host.username
    prop_title = booking.property.title
    if booking.payment_auth_status == "captured":
        extra = (
            " Payment had already been captured on Qasha. "
            "Use Help if you need a refund."
        )
    elif booking.payment_auth_status == "released":
        extra = " Your card authorization was released — no charge was made."
    else:
        extra = ""
    body = (
        f"{host_name} cancelled your booking request for \"{prop_title}\".{extra}\n\n"
        f"Message them here if you need more information."
    )
    _create_guest_notification(booking, body)
