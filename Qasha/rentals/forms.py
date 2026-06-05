from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date
from decimal import Decimal

from .amenity_utils import (
    MAX_AMENITIES,
    MAX_AMENITIES_PER_LISTING,
    parse_custom_amenity_lines,
    validate_custom_amenity_name,
)
from .models import Property, PropertyImage, PropertyAmenity, Booking, Message, Review, Amenity
from .booking_utils import validate_booking_dates
from core.maps_utils import places_autocomplete_enabled
from .media_utils import ALLOWED_VIDEO_EXTENSIONS, VIDEO_ACCEPT_INPUT, video_extension_allowed
from users.tiers import get_photo_limit, user_can_upload_video, user_has_full_listing_access, validate_video_file

User = get_user_model()

STANDARD_LISTING_COPY = (
    "Please use Qasha messages to talk to people who want to rent. Do not put phone numbers or "
    "WhatsApp in the listing — chat here first."
)


class PropertyForm(forms.ModelForm):
    """Simplified listing form: no free-text title/description, no coordinates."""

    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.filter(is_custom=False).order_by('category', 'name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Standard amenities',
        help_text=f'Tick what this place has — up to {MAX_AMENITIES} amenities in total (including any you add below).',
    )
    custom_amenities = forms.CharField(
        required=False,
        label='Add your own',
        help_text=f'Can’t find it above? Type up to {MAX_AMENITIES} in total — one per line (e.g. Rooftop deck).',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'One per line, e.g.\nRooftop deck\nBorehole water',
            }
        ),
    )
    declare_authorized = forms.BooleanField(
        required=False,
        label='I am the owner or have permission from the owner to list this property.',
    )
    declare_accurate = forms.BooleanField(
        required=False,
        label='The details I provide are accurate to the best of my knowledge.',
    )
    declare_media_rights = forms.BooleanField(
        required=False,
        label='Photos and video are mine, or I have rights to use them on Qasha.',
    )
    accept_listing_terms = forms.BooleanField(
        required=False,
        label='I agree to the Terms of Service and Privacy Policy for this listing.',
    )
    custom_property_type = forms.CharField(
        required=False,
        max_length=80,
        label='Describe the place type',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg rounded-4',
                'placeholder': 'e.g. Office space, shop, warehouse',
            }
        ),
    )

    class Meta:
        model = Property
        fields = [
            "property_type",
            "furnishing",
            "lease_type",
            "address",
            "suburb",
            "city",
            "payment_preference",
            "monthly_rent",
            "nightly_rate",
            "secure_space_amount",
            "utilities_included",
            "bedrooms",
            "bathrooms",
            "area_sqm",
            "max_occupants",
            "available_from",
            "is_available",
            "video",
        ]
        widgets = {
            "property_type": forms.Select(attrs={"class": "form-select form-select-lg rounded-4"}),
            "furnishing": forms.Select(attrs={"class": "form-select form-select-lg rounded-4"}),
            "lease_type": forms.HiddenInput(),
            "address": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg rounded-4",
                    "placeholder": "Start typing your address…",
                    "autocomplete": "off",
                    "data-qasha-places": "listing",
                }
            ),
            "suburb": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg rounded-4",
                    "placeholder": "Suburb / township",
                    "autocomplete": "off",
                    "data-qasha-places": "suburb",
                    "data-qasha-city-field": "id_city",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg rounded-4",
                    "placeholder": "City",
                    "autocomplete": "off",
                }
            ),
            "payment_preference": forms.RadioSelect(attrs={"class": "payment-radio"}),
            "monthly_rent": forms.NumberInput(
                attrs={"class": "form-control form-control-lg rounded-4", "step": "0.01", "placeholder": "e.g. 8500"}
            ),
            "nightly_rate": forms.NumberInput(
                attrs={"class": "form-control form-control-lg rounded-4", "step": "0.01", "placeholder": "e.g. 650"}
            ),
            "secure_space_amount": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg rounded-4",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "e.g. 5000",
                }
            ),
            "utilities_included": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "bedrooms": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg rounded-4",
                    "min": "0",
                    "placeholder": "0 if studio / open plan",
                }
            ),
            "bathrooms": forms.NumberInput(
                attrs={"class": "form-control form-control-lg rounded-4", "min": "0", "placeholder": "Optional"}
            ),
            "max_occupants": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-lg rounded-4",
                    "min": "1",
                    "placeholder": "1",
                }
            ),
            "area_sqm": forms.NumberInput(
                attrs={"class": "form-control form-control-lg rounded-4", "min": "0", "placeholder": "Optional"}
            ),
            "available_from": forms.DateInput(attrs={"class": "form-control form-control-lg rounded-4", "type": "date"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "video": forms.FileInput(
                attrs={
                    "class": "form-control form-control-lg rounded-4",
                    "accept": VIDEO_ACCEPT_INPUT,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["lease_type"].widget = forms.HiddenInput()
        self.fields["lease_type"].required = True
        self.fields["payment_preference"].help_text = (
            "Pick one: pay on Qasha to secure the space, or pay the owner yourself. You can still message each other on Qasha first."
        )
        self.fields["secure_space_amount"].label = "Amount to secure this space (ZAR)"
        self.fields["secure_space_amount"].required = False
        self.fields["secure_space_amount"].widget.attrs["min"] = "0.01"
        self.fields["bedrooms"].required = False
        self.fields["bathrooms"].required = False
        self.fields["max_occupants"].required = False
        user = self.request.user if self.request and self.request.user.is_authenticated else None
        self.photo_limit = get_photo_limit(user) if user else 10
        if not places_autocomplete_enabled():
            for name, placeholder in (
                ('address', 'e.g. 12 Main Road or area name'),
                ('suburb', 'Suburb or township'),
                ('city', 'City or town'),
            ):
                if name not in self.fields:
                    continue
                field = self.fields[name]
                attrs = field.widget.attrs.copy()
                attrs.pop('data-qasha-places', None)
                attrs.pop('data-qasha-city-field', None)
                attrs['placeholder'] = placeholder
                field.widget = forms.TextInput(attrs=attrs)
        if user and not user_can_upload_video(user):
            self.fields.pop("video", None)
        elif "video" in self.fields:
            self.fields["video"].help_text = (
                "Verified hosts: one video, up to 3 minutes. "
                f"Upload: {', '.join(ext.upper() for ext in ALLOWED_VIDEO_EXTENSIONS)}. "
                "MP4 (H.264) plays on all phones; other formats may not preview in the browser."
            )
        self.fields["latitude"] = forms.DecimalField(
            required=False,
            widget=forms.HiddenInput(attrs={"id": "id_latitude"}),
        )
        self.fields["longitude"] = forms.DecimalField(
            required=False,
            widget=forms.HiddenInput(attrs={"id": "id_longitude"}),
        )
        if self.instance and self.instance.pk:
            if self.instance.latitude is not None:
                self.fields["latitude"].initial = self.instance.latitude
            if self.instance.longitude is not None:
                self.fields["longitude"].initial = self.instance.longitude
        self.fields['amenities'].widget.attrs['class'] = 'amenity-checklist'
        if self.instance and self.instance.pk:
            linked = self.instance.property_amenities.select_related('amenity')
            self.fields['amenities'].initial = [
                pa.amenity for pa in linked if not pa.amenity.is_custom
            ]
            custom_names = [pa.amenity.name for pa in linked if pa.amenity.is_custom]
            self.fields['custom_amenities'].initial = '\n'.join(custom_names)
            if self.instance.property_type == 'other' and self.instance.property_type_custom:
                self.fields['custom_property_type'].initial = self.instance.property_type_custom
            for name in (
                'declare_authorized',
                'declare_accurate',
                'declare_media_rights',
                'accept_listing_terms',
            ):
                self.fields.pop(name, None)
        else:
            for name in (
                'declare_authorized',
                'declare_accurate',
                'declare_media_rights',
                'accept_listing_terms',
            ):
                self.fields[name].required = True
                self.fields[name].widget.attrs['class'] = 'form-check-input'

    def clean(self):
        cleaned = super().clean()
        lease_type = cleaned.get("lease_type")
        monthly_rent = cleaned.get("monthly_rent")
        nightly_rate = cleaned.get("nightly_rate")
        available_from = cleaned.get("available_from")

        if lease_type in ("monthly", "both") and not monthly_rent:
            self.add_error("monthly_rent", "Fill in the rent per month.")
        if lease_type in ("short_stay", "both") and not nightly_rate:
            self.add_error("nightly_rate", "Fill in the price per night.")

        property_type = cleaned.get("property_type")
        custom_type = (cleaned.get("custom_property_type") or "").strip()
        if property_type == "other":
            if not custom_type:
                self.add_error("custom_property_type", "Describe what type of place this is.")
            elif len(custom_type) < 2:
                self.add_error("custom_property_type", "Please enter at least 2 characters.")
        else:
            cleaned["custom_property_type"] = ""

        payment_preference = cleaned.get("payment_preference") or "platform"
        secure_amount = cleaned.get("secure_space_amount") or Decimal("0")
        if payment_preference == "direct":
            cleaned["secure_space_amount"] = Decimal("0")
            cleaned["deposit_amount"] = Decimal("0")
        else:
            cleaned["payment_preference"] = "platform"
            if secure_amount <= 0:
                self.add_error(
                    "secure_space_amount",
                    "Required — tenants pay this on Qasha to secure the space.",
                )
            else:
                cleaned["secure_space_amount"] = secure_amount

        if available_from and available_from < date.today():
            self.add_error(
                "available_from",
                "Available-from date cannot be before today. Choose today or a future date.",
            )

        if cleaned.get("bedrooms") in (None, ""):
            cleaned["bedrooms"] = 0
        if cleaned.get("max_occupants") in (None, ""):
            cleaned["max_occupants"] = 1
        if cleaned.get("bathrooms") in (None, ""):
            cleaned["bathrooms"] = 1

        images = []
        if self.request:
            images = self.request.FILES.getlist("property_images")
        is_new = not (self.instance and self.instance.pk)
        existing_count = self.instance.images.count() if self.instance and self.instance.pk else 0
        remove_count = 0
        if self.request and self.instance and self.instance.pk:
            raw_remove = self.request.POST.getlist('remove_image_ids')
            remove_ids = []
            for raw in raw_remove:
                try:
                    remove_ids.append(int(raw))
                except ValueError:
                    continue
            if remove_ids:
                remove_count = self.instance.images.filter(pk__in=remove_ids).count()

        user = self.request.user if self.request and self.request.user.is_authenticated else None
        if user:
            limit = get_photo_limit(user)
            existing_after_remove = max(0, existing_count - remove_count)
            total_after = existing_after_remove + len(images)
            if total_after > limit:
                tier_name = "Verified" if user_has_full_listing_access(user) else "Standard"
                raise ValidationError(
                    f"{tier_name} accounts can have up to {limit} photos per listing. "
                    f"You have {existing_after_remove} after removals and tried to add {len(images)}."
                )
            if is_new and places_autocomplete_enabled() and not (
                cleaned.get('latitude') and cleaned.get('longitude')
            ):
                self.add_error(
                    'address',
                    'Pick your address from the Google suggestions so renters can find it on the map.',
                )
        selected = list(cleaned.get('amenities') or [])
        custom_names = parse_custom_amenity_lines(cleaned.get('custom_amenities', ''))
        standard_names_lower = {
            a.name.lower()
            for a in Amenity.objects.filter(is_custom=False).only('name')
        }
        for name in custom_names:
            err = validate_custom_amenity_name(name, standard_names_lower)
            if err:
                self.add_error('custom_amenities', err)
                break

        if len(custom_names) > MAX_AMENITIES:
            self.add_error(
                'custom_amenities',
                f'You can add at most {MAX_AMENITIES} amenities in total.',
            )
        total = len(selected) + len(custom_names)
        if total > MAX_AMENITIES:
            self.add_error(
                'amenities',
                f'Choose at most {MAX_AMENITIES} amenities in total '
                f'({len(selected)} ticked + {len(custom_names)} typed).',
            )
        cleaned['custom_amenity_names'] = custom_names

        return cleaned

    def clean_video(self):
        uploaded = self.request.FILES.get('video') if self.request else None
        if not uploaded:
            if self.instance and self.instance.pk and self.instance.video:
                return self.instance.video
            return None
        user = self.request.user if self.request and self.request.user.is_authenticated else None
        if not user or not user_can_upload_video(user):
            raise ValidationError('Video uploads are for verified hosts. Apply under Promote & verify.')
        if not video_extension_allowed(uploaded.name):
            raise ValidationError(
                'Unsupported video type. Use MP4, MOV, WebM, M4V, 3GP, AVI, MKV, or MPEG.'
            )
        try:
            validate_video_file(uploaded)
        except ValueError as exc:
            raise ValidationError(str(exc))
        uploaded.seek(0)
        return uploaded

    def save(self, commit=True):
        obj = super().save(commit=False)
        custom_type = (self.cleaned_data.get("custom_property_type") or "").strip()
        if obj.property_type == "other" and custom_type:
            type_label = custom_type
            obj.property_type_custom = custom_type
        else:
            type_label = dict(Property.PROPERTY_TYPES).get(obj.property_type, obj.property_type)
            obj.property_type_custom = ""
        obj.title = f"{type_label} · {obj.suburb}, {obj.city}"[:200]
        obj.description = STANDARD_LISTING_COPY
        lat = self.cleaned_data.get("latitude")
        lng = self.cleaned_data.get("longitude")
        if self.instance.pk:
            addr_changed = (
                self.instance.address != obj.address
                or self.instance.suburb != obj.suburb
                or self.instance.city != obj.city
            )
            if addr_changed:
                if lat is not None and lng is not None:
                    obj.latitude = lat
                    obj.longitude = lng
                else:
                    obj.latitude = None
                    obj.longitude = None
            elif lat is not None and lng is not None:
                obj.latitude = lat
                obj.longitude = lng
            else:
                obj.latitude = self.instance.latitude
                obj.longitude = self.instance.longitude
        elif lat is not None and lng is not None:
            obj.latitude = lat
            obj.longitude = lng
        user = self.request.user if self.request and self.request.user.is_authenticated else None
        new_video = self.request.FILES.get('video') if self.request else None
        if user and not user_can_upload_video(user):
            if self.instance.pk and self.instance.video:
                obj.video = self.instance.video
            else:
                obj.video = None
        elif not new_video and self.instance.pk and self.instance.video:
            obj.video = self.instance.video
        if obj.payment_preference == "direct":
            obj.secure_space_amount = Decimal("0")
            obj.deposit_amount = Decimal("0")
        elif not obj.deposit_amount:
            obj.deposit_amount = obj.secure_space_amount or Decimal('0')
        if commit:
            obj.save()
            self._save_amenities(obj)
        return obj

    def _save_amenities(self, prop):
        selected = list(self.cleaned_data.get('amenities') or [])
        custom_names = self.cleaned_data.get('custom_amenity_names') or []
        user = self.request.user if self.request and self.request.user.is_authenticated else None

        amenity_objects = list(selected)
        for name in custom_names:
            amenity = Amenity.objects.filter(name__iexact=name).first()
            if not amenity:
                amenity = Amenity.objects.create(
                    name=name,
                    category='Custom',
                    icon='fas fa-tag',
                    is_custom=True,
                    created_by=user,
                )
            amenity_objects.append(amenity)

        target_ids = {a.pk for a in amenity_objects}
        prop.property_amenities.exclude(amenity_id__in=target_ids).delete()
        existing_ids = set(prop.property_amenities.values_list('amenity_id', flat=True))
        for amenity in amenity_objects:
            if amenity.pk not in existing_ids:
                PropertyAmenity.objects.create(property=prop, amenity=amenity)


class PropertyImageForm(forms.ModelForm):
    """Form for uploading property images"""

    class Meta:
        model = PropertyImage
        fields = ["image", "caption", "is_primary"]
        widgets = {
            "image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "caption": forms.TextInput(attrs={"class": "form-control", "placeholder": "Image caption (optional)"}),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class BookingForm(forms.ModelForm):
    """Apply to rent or book a short stay."""

    checkout_unknown = forms.BooleanField(
        required=False,
        label="I don't know my check-out date yet",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_checkout_unknown"}),
    )

    class Meta:
        model = Booking
        fields = ["check_in_date", "check_out_date", "special_requests"]
        widgets = {
            "check_in_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "check_out_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "placeholder": "Optional for monthly"}
            ),
            "special_requests": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Tell the owner about yourself or your move-in plans…",
                }
            ),
        }

    def __init__(self, *args, property_obj=None, **kwargs):
        self.property_obj = property_obj
        super().__init__(*args, **kwargs)
        is_short_only = property_obj and property_obj.lease_type == "short_stay"
        is_monthly = property_obj and property_obj.lease_type in ("monthly", "both") and property_obj.monthly_rent
        if is_monthly and not is_short_only:
            self.fields["check_in_date"].label = "Move-in date"
            self.fields["check_out_date"].required = False
            self.fields["check_out_date"].help_text = (
                "Optional. Leave blank or tick below if your stay is open-ended."
            )
        elif is_short_only:
            self.fields["check_out_date"].label = "Check-out date"
            self.fields["check_out_date"].help_text = "Required for short stays."
            self.fields.pop("checkout_unknown", None)
        else:
            self.fields["check_out_date"].help_text = "Leave blank if you are not sure yet — the owner can confirm dates with you."

    def clean_special_requests(self):
        from users.validators import validate_no_peer_contact_in_text

        return validate_no_peer_contact_in_text(
            self.cleaned_data.get('special_requests', ''),
            field_label='Note to the owner',
        )

    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get("check_in_date")
        check_out_date = cleaned_data.get("check_out_date")
        checkout_unknown = cleaned_data.get("checkout_unknown")
        prop = self.property_obj

        if checkout_unknown:
            cleaned_data["check_out_date"] = None
            check_out_date = None

        try:
            validate_booking_dates(
                prop,
                check_in_date,
                check_out_date,
                checkout_unknown=bool(checkout_unknown),
            )
        except ValidationError as exc:
            raise ValidationError(exc.messages)

        return cleaned_data


class BookingPaymentForm(forms.Form):
    """Card details collected at application; charged when the host accepts."""

    cardholder_name = forms.CharField(
        max_length=120,
        label="Name on card",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "As shown on your card", "autocomplete": "cc-name"}
        ),
    )
    card_number = forms.CharField(
        max_length=19,
        label="Card number",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "4111 1111 1111 1111",
                "inputmode": "numeric",
                "autocomplete": "cc-number",
            }
        ),
    )
    card_expiry = forms.CharField(
        max_length=9,
        label="Expiry (MM/YY)",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "MM/YY",
                "autocomplete": "cc-exp",
                "maxlength": "7",
                "inputmode": "numeric",
            }
        ),
    )
    card_cvv = forms.CharField(
        max_length=4,
        label="CVV",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "123", "autocomplete": "cc-csc"}
        ),
    )

    def clean_card_number(self):
        raw = self.cleaned_data.get("card_number", "")
        digits = "".join(c for c in raw if c.isdigit())
        if len(digits) < 13 or len(digits) > 19:
            raise ValidationError("Enter a valid card number (13–19 digits).")
        return digits

    def clean(self):
        cleaned = super().clean()
        card_number = cleaned.get("card_number")
        if card_number:
            cleaned["card_last4"] = card_number[-4:]
        return cleaned

    def clean_card_expiry(self):
        raw = (self.cleaned_data.get("card_expiry") or "").strip().replace(" ", "")
        digits_only = "".join(c for c in raw if c.isdigit())
        if "/" in raw:
            parts = raw.split("/", 1)
            month_part = "".join(c for c in parts[0] if c.isdigit())
            year_part = "".join(c for c in parts[1] if c.isdigit())
        elif len(digits_only) in (4, 6):
            month_part = digits_only[:2]
            year_part = digits_only[2:]
        else:
            month_part = ""
            year_part = ""

        if len(year_part) == 4:
            year_part = year_part[2:]
        if len(month_part) != 2 or len(year_part) != 2:
            raise ValidationError("Use MM/YY (e.g. 12/28).")

        try:
            month = int(month_part)
            year = int(year_part)
        except ValueError as exc:
            raise ValidationError("Use MM/YY (e.g. 12/28).") from exc
        if month < 1 or month > 12:
            raise ValidationError("Invalid expiry month.")
        exp_year = 2000 + year
        today = date.today()
        if (exp_year, month) < (today.year, today.month):
            raise ValidationError("This card has expired.")
        return f"{month:02d}/{year:02d}"

    def clean_card_cvv(self):
        raw = self.cleaned_data.get("card_cvv", "")
        if not raw.isdigit() or len(raw) not in (3, 4):
            raise ValidationError("Enter a valid CVV.")
        return raw

class MessageForm(forms.ModelForm):
    """Form for sending messages (no subject line)."""

    class Meta:
        model = Message
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Write your message…",
                }
            ),
        }

    def clean_message(self):
        from users.validators import validate_no_peer_contact_in_text

        return validate_no_peer_contact_in_text(
            self.cleaned_data.get('message', ''),
            field_label='Message',
            required=True,
        )


class ReviewForm(forms.ModelForm):
    """Private feedback for the host and platform moderation."""

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(
                attrs={"class": "form-select"},
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Only the owner and Qasha see this. It is not shown publicly.",
                }
            ),
        }


class PropertySearchForm(forms.Form):
    """Form for property search and filtering"""

    PROPERTY_TYPES = [
        ("", "All Types"),
        ("room", "Room"),
        ("apartment", "Apartment"),
        ("house", "House"),
        ("studio", "Studio"),
    ]

    FURNISHING_TYPES = [
        ("", "All Furnishing"),
        ("furnished", "Furnished"),
        ("unfurnished", "Unfurnished"),
        ("semi_furnished", "Semi-furnished"),
    ]

    LEASE_TYPES = [
        ("", "All Lease Types"),
        ("monthly", "Monthly"),
        ("short_stay", "Short Stay"),
        ("both", "Both"),
    ]

    SORT_OPTIONS = [
        ("newest", "Newest First"),
        ("price_low", "Price: Low to High"),
        ("price_high", "Price: High to Low"),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Search by location, property type, or keywords..."}
        ),
    )

    property_type = forms.ChoiceField(
        choices=PROPERTY_TYPES, required=False, widget=forms.Select(attrs={"class": "form-control"})
    )

    furnishing = forms.ChoiceField(
        choices=FURNISHING_TYPES, required=False, widget=forms.Select(attrs={"class": "form-control"})
    )

    lease_type = forms.ChoiceField(
        choices=LEASE_TYPES, required=False, widget=forms.Select(attrs={"class": "form-control"})
    )

    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Min Price", "step": "0.01"}),
    )

    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Max Price", "step": "0.01"}),
    )

    bedrooms = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Min Bedrooms", "min": "0"}),
    )

    pet_friendly = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    sort = forms.ChoiceField(
        choices=SORT_OPTIONS, required=False, widget=forms.Select(attrs={"class": "form-control"})
    )
