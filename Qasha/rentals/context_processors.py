"""Template context: nav badges for messages and booking actions."""

from .models import Booking, Message


def nav_alerts(request):
    ctx = {
        "unread_message_count": 0,
        "pending_host_booking_count": 0,
        "guest_booking_action_count": 0,
        "booking_nav_count": 0,
    }
    if not request.user.is_authenticated:
        return ctx

    user = request.user
    ctx["unread_message_count"] = Message.objects.filter(
        recipient=user, is_read=False
    ).count()
    ctx["pending_host_booking_count"] = Booking.objects.filter(
        property__host=user,
        status="pending",
    ).count()
    # Direct-payment listings only: guest arranges payment after accept (platform auto-charges).
    ctx["guest_booking_action_count"] = Booking.objects.filter(
        guest=user,
        status="accepted",
        property__payment_preference="direct",
    ).count()
    ctx["booking_nav_count"] = (
        ctx["pending_host_booking_count"] + ctx["guest_booking_action_count"]
    )
    return ctx
