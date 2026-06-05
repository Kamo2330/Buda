"""Listing form helpers — field-to-section mapping for validation UX."""

LISTING_SECTIONS = {
    'photos': {'id': 'section-photos', 'label': 'Photos and video', 'icon': 'fa-camera'},
    'lease': {'id': 'section-lease', 'label': 'How do you rent it?', 'icon': 'fa-calendar-alt'},
    'where': {'id': 'section-where', 'label': 'Where is it?', 'icon': 'fa-map-marker-alt'},
    'about': {'id': 'section-about', 'label': 'About the place', 'icon': 'fa-home'},
    'money': {'id': 'section-money', 'label': 'Money', 'icon': 'fa-tag'},
    'payment': {'id': 'section-payment', 'label': 'How will they pay?', 'icon': 'fa-wallet'},
    'availability': {'id': 'section-availability', 'label': 'When is it free?', 'icon': 'fa-door-open'},
    'legal': {'id': 'section-legal', 'label': 'Before you publish', 'icon': 'fa-file-signature'},
}

FIELD_TO_SECTION = {
    'property_images': 'photos',
    'video': 'photos',
    'lease_type': 'lease',
    'address': 'where',
    'suburb': 'where',
    'city': 'where',
    'property_type': 'about',
    'custom_property_type': 'about',
    'furnishing': 'about',
    'bedrooms': 'about',
    'bathrooms': 'about',
    'max_occupants': 'about',
    'area_sqm': 'about',
    'amenities': 'about',
    'custom_amenities': 'about',
    'monthly_rent': 'money',
    'nightly_rate': 'money',
    'utilities_included': 'money',
    'payment_preference': 'payment',
    'secure_space_amount': 'payment',
    'available_from': 'availability',
    'is_available': 'availability',
    'declare_authorized': 'legal',
    'declare_accurate': 'legal',
    'declare_media_rights': 'legal',
    'accept_listing_terms': 'legal',
}


def listing_form_error_context(form):
    """Build section-grouped errors for the listing form template."""
    sections_hit = {}
    for field_name, errors in form.errors.items():
        section_key = FIELD_TO_SECTION.get(field_name, 'about')
        if section_key not in sections_hit:
            sections_hit[section_key] = []
        label = field_name.replace('_', ' ').title()
        if field_name in form.fields:
            label = form.fields[field_name].label or label
        for err in errors:
            sections_hit[section_key].append({'field': field_name, 'label': label, 'message': err})

    if form.non_field_errors():
        sections_hit.setdefault('about', [])
        for err in form.non_field_errors():
            sections_hit['about'].append({'field': '', 'label': 'Listing', 'message': err})

    section_errors = []
    for key, meta in LISTING_SECTIONS.items():
        if key in sections_hit:
            section_errors.append({
                'key': key,
                'id': meta['id'],
                'label': meta['label'],
                'icon': meta['icon'],
                'items': sections_hit[key],
            })
    return {
        'listing_section_errors': section_errors,
        'listing_sections': LISTING_SECTIONS,
        'field_to_section': FIELD_TO_SECTION,
    }


def listing_video_upload_context():
    from users.tiers import PREMIUM_MAX_VIDEO_BYTES, PREMIUM_MAX_VIDEO_SECONDS

    return {
        'max_video_bytes': PREMIUM_MAX_VIDEO_BYTES,
        'max_video_mb': PREMIUM_MAX_VIDEO_BYTES // (1024 * 1024),
        'max_video_minutes': PREMIUM_MAX_VIDEO_SECONDS // 60,
    }
