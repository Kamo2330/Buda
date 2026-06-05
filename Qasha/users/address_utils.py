"""Parse South African free-text home addresses when Google Places is unavailable."""


def parse_sa_home_address(address: str) -> tuple[str, str]:
    """
    Split a typed address into suburb and city.
    Examples:
      "12 Main Rd, Sandton, Johannesburg" -> Sandton, Johannesburg
      "Sandton, Johannesburg" -> Sandton, Johannesburg
      "Soweto" -> '', Soweto
    """
    text = (address or '').strip()
    if not text:
        return '', ''

    parts = [p.strip() for p in text.split(',') if p.strip()]
    if len(parts) >= 3:
        return parts[-2], parts[-1]
    if len(parts) == 2:
        return parts[0], parts[1]
    return '', parts[0]
