"""Amenity limits and parsing for listings and filters."""

import re

MAX_AMENITIES = 5
CUSTOM_AMENITY_MAX_LENGTH = 80

_CONTACT_PATTERN = re.compile(
    r"(\+?\d[\d\s\-]{8,}\d|@\w+\.\w+|whatsapp|wa\.me)",
    re.IGNORECASE,
)

# Backwards-compatible aliases
MAX_AMENITIES_PER_LISTING = MAX_AMENITIES


def parse_custom_amenity_lines(raw: str) -> list[str]:
    """Split textarea input into unique amenity names (one per line)."""
    seen = set()
    names = []
    for line in (raw or "").splitlines():
        name = " ".join(line.strip().split())
        if len(name) < 2:
            continue
        if len(name) > CUSTOM_AMENITY_MAX_LENGTH:
            name = name[:CUSTOM_AMENITY_MAX_LENGTH].rstrip()
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def cap_amenity_selection(standard_ids: list, custom_names: list[str]) -> tuple[list, list[str]]:
    """Keep at most MAX_AMENITIES items combined (standard IDs first, then custom names)."""
    ids = list(standard_ids)[:MAX_AMENITIES]
    remaining = MAX_AMENITIES - len(ids)
    names = custom_names[: max(0, remaining)]
    return ids, names


def amenity_filter_error(standard_ids: list, custom_names: list[str]) -> str | None:
    """Return an error message if browse filters exceed the amenity cap."""
    total = len(standard_ids) + len(custom_names)
    if total > MAX_AMENITIES:
        return f'Choose at most {MAX_AMENITIES} amenities in filters.'
    return None


def validate_custom_amenity_name(name: str, standard_names_lower: set[str]) -> str | None:
    """Return an error message if invalid, else None."""
    if len(name) < 2:
        return "Each custom amenity needs at least 2 characters."
    if _CONTACT_PATTERN.search(name):
        return "Do not put phone numbers or email in amenity names."
    if name.lower() in standard_names_lower:
        return f'"{name}" is already in the list above — tick it there instead.'
    return None
