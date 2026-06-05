"""Template tags for Qasha (ZAR formatting, etc.)."""

from decimal import Decimal, InvalidOperation

from django import template

from rentals.media_utils import mime_type_for_video, stored_media_exists

register = template.Library()


@register.filter
def media_exists(file_field):
    """True when a FileField/ImageField points at a file that exists in storage."""
    return stored_media_exists(file_field)


def _to_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


@register.filter
def zar(value, arg=0):
    """
    Format a number as South African Rand, e.g. R 12,500 or R 12,500.50.
    Usage: {{ price|zar }} or {{ price|zar:2 }}
    """
    amount = _to_decimal(value)
    if amount is None:
        return ""

    try:
        places = int(arg)
    except (TypeError, ValueError):
        places = 0

    if places <= 0:
        quantized = amount.quantize(Decimal("1"))
        body = f"{int(quantized):,}"
    else:
        fmt = f"{{0:,.{places}f}}"
        body = fmt.format(float(amount))

    return f"R {body}"


@register.filter
def video_mime_type(filename):
    """MIME type for HTML5 video source from a stored filename."""
    return mime_type_for_video(filename)
