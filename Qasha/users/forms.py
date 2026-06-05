from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from .address_utils import parse_sa_home_address
from .models import UserProfile
from .validators import (
    validate_no_contact_in_text,
    validate_person_name,
    validate_platform_phone,
)
from rentals.geo_utils import (
    DEFAULT_RADIUS_KM,
    RADIUS_FORM_CHOICES,
    clamp_radius_km,
)
from core.maps_utils import places_autocomplete_enabled

User = get_user_model()


def _save_profile_home(profile, cleaned):
    profile.home_address = (cleaned.get("home_address") or "").strip()
    profile.home_suburb = (cleaned.get("home_suburb") or "").strip()
    profile.home_city = (cleaned.get("home_city") or "").strip()
    profile.home_latitude = cleaned.get("home_latitude")
    profile.home_longitude = cleaned.get("home_longitude")
    profile.location = profile.area_label()
    if "search_radius_km" in cleaned:
        profile.search_radius_km = clamp_radius_km(
            cleaned.get("search_radius_km"), DEFAULT_RADIUS_KM
        )
    if "widen_search_if_empty" in cleaned:
        profile.widen_search_if_empty = bool(cleaned.get("widen_search_if_empty"))
    profile.save(
        update_fields=[
            "home_address",
            "home_suburb",
            "home_city",
            "home_latitude",
            "home_longitude",
            "location",
            "search_radius_km",
            "widen_search_if_empty",
        ]
    )


class HomeLocationFieldsMixin(forms.Form):
    """Google Places–backed home area (signup + profile)."""

    home_address = forms.CharField(
        max_length=200,
        label="Where do you live?",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Start typing your address or suburb…",
                "autocomplete": "off",
                "data-qasha-places": "home",
            }
        ),
    )
    home_suburb = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_home_suburb"}),
    )
    home_city = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_home_city"}),
    )
    home_latitude = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_home_latitude"}),
    )
    home_longitude = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_home_longitude"}),
    )

    def clean_home_latitude(self):
        return self._optional_decimal(self.cleaned_data.get("home_latitude"))

    def clean_home_longitude(self):
        return self._optional_decimal(self.cleaned_data.get("home_longitude"))

    def clean_home_address(self):
        value = (self.cleaned_data.get('home_address') or '').strip()
        if value:
            validate_no_contact_in_text(value, field_label='Home address')
        return value

    def _optional_decimal(self, raw):
        if raw in (None, ""):
            return None
        try:
            return Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return None

    def configure_home_places_widgets(self):
        if places_autocomplete_enabled() or 'home_address' not in self.fields:
            return
        attrs = self.fields['home_address'].widget.attrs.copy()
        attrs.pop('data-qasha-places', None)
        attrs['placeholder'] = 'e.g. Sandton, Johannesburg or 12 Main Rd, Sandton'
        self.fields['home_address'].widget.attrs = attrs

    def clean_home_location(self):
        address = (self.cleaned_data.get('home_address') or '').strip()
        if not address:
            raise ValidationError('Enter where you live (suburb and city).')

        suburb = (self.cleaned_data.get('home_suburb') or '').strip()
        city = (self.cleaned_data.get('home_city') or '').strip()
        lat = self.cleaned_data.get('home_latitude')
        lng = self.cleaned_data.get('home_longitude')

        if not suburb or not city:
            parsed_suburb, parsed_city = parse_sa_home_address(address)
            if not suburb and parsed_suburb:
                suburb = parsed_suburb
                self.cleaned_data['home_suburb'] = parsed_suburb
            if not city and parsed_city:
                city = parsed_city
                self.cleaned_data['home_city'] = parsed_city

        if not city and len(address) >= 3:
            city = address
            self.cleaned_data['home_city'] = city

        if not city:
            raise ValidationError(
                'Add your area, e.g. Sandton, Johannesburg or Soweto, Gauteng.'
            )

        if places_autocomplete_enabled() and (lat is None or lng is None):
            if ',' not in address and len(address.split()) < 2 and not suburb:
                raise ValidationError(
                    'Choose a suggested address from the list, or type suburb and city separated by a comma.'
                )


class UserRegistrationForm(UserCreationForm, HomeLocationFieldsMixin):
    """One account for everyone — browse, book, list, and message on Qasha."""

    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        required=True,
        max_length=20,
        label='Phone number',
    )
    accept_terms = forms.BooleanField(
        required=True,
        label="I agree to the Terms of Service and Privacy Policy",
        error_messages={"required": "You must accept the Terms and Privacy Policy to register."},
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure_home_places_widgets()
        for name, field in self.fields.items():
            if name == "accept_terms":
                field.widget.attrs["class"] = "form-check-input"
                continue
            if name.startswith("home_") and name not in ("home_address",):
                continue
            field.widget.attrs.setdefault("class", "form-control")

    def clean_first_name(self):
        return validate_person_name(self.cleaned_data.get('first_name', ''), field_label='First name')

    def clean_last_name(self):
        return validate_person_name(self.cleaned_data.get('last_name', ''), field_label='Last name')

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('This email is already used on another account.')
        return email

    def clean_phone_number(self):
        return validate_platform_phone(self.cleaned_data.get('phone_number', ''))

    def clean(self):
        cleaned = super().clean()
        if cleaned is not None:
            try:
                self.clean_home_location()
            except ValidationError as exc:
                self.add_error("home_address", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data["phone_number"]
        user.is_host = False
        if self.cleaned_data.get("accept_terms"):
            user.terms_accepted_at = timezone.now()
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            _save_profile_home(profile, self.cleaned_data)
        return user


class ManageProfileForm(HomeLocationFieldsMixin):
    """Edit account and public profile from Manage."""

    first_name = forms.CharField(max_length=150, required=False, label='First name')
    last_name = forms.CharField(max_length=150, required=False, label='Last name')
    email = forms.EmailField(label='Email')
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        label='Phone number',
    )
    profile_picture = forms.ImageField(
        required=False,
        label="Profile photo",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )
    bio = forms.CharField(
        required=False,
        label="About you",
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'A short intro (optional)',
            }
        ),
    )
    search_radius_km = forms.TypedChoiceField(
        choices=RADIUS_FORM_CHOICES,
        coerce=int,
        label="Default search radius",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    widen_search_if_empty = forms.BooleanField(
        required=False,
        label="Wider search if no results",
        help_text="If nothing is in your radius, automatically search up to 200 km.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        self._profile = profile
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields['email'].initial = user.email
        self.fields['phone_number'].initial = user.phone_number
        self.fields['bio'].initial = profile.bio
        if "home_address" in self.fields:
            self.fields["home_address"].initial = profile.home_address or profile.location
        if "home_suburb" in self.fields:
            self.fields["home_suburb"].initial = profile.home_suburb
        if "home_city" in self.fields:
            self.fields["home_city"].initial = profile.home_city
        if "home_latitude" in self.fields and profile.home_latitude is not None:
            self.fields["home_latitude"].initial = profile.home_latitude
        if "home_longitude" in self.fields and profile.home_longitude is not None:
            self.fields["home_longitude"].initial = profile.home_longitude
        self.fields["search_radius_km"].initial = clamp_radius_km(
            profile.search_radius_km, DEFAULT_RADIUS_KM
        )
        self.fields["widen_search_if_empty"].initial = profile.widen_search_if_empty
        self.configure_home_places_widgets()
        for name in ('first_name', 'last_name', 'email', 'phone_number'):
            self.fields[name].widget.attrs.setdefault('class', 'form-control')

    def _home_location_changed(self, cleaned) -> bool:
        if not self.is_bound:
            return True
        profile = self._profile
        checks = (
            ('home_address', profile.home_address or profile.location or ''),
            ('home_suburb', profile.home_suburb or ''),
            ('home_city', profile.home_city or ''),
        )
        for field, initial in checks:
            if (cleaned.get(field) or '').strip() != (initial or '').strip():
                return True
        for field, attr in (('home_latitude', 'home_latitude'), ('home_longitude', 'home_longitude')):
            new_val = cleaned.get(field)
            old_val = getattr(profile, attr, None)
            if new_val != old_val:
                return True
        return False

    def clean(self):
        cleaned = super().clean()
        if cleaned is not None and self._home_location_changed(cleaned):
            try:
                self.clean_home_location()
            except ValidationError as exc:
                self.add_error('home_address', exc)
        return cleaned

    def clean_first_name(self):
        return validate_person_name(self.cleaned_data.get('first_name', ''), field_label='First name')

    def clean_last_name(self):
        return validate_person_name(self.cleaned_data.get('last_name', ''), field_label='Last name')

    def clean_bio(self):
        return validate_no_contact_in_text(
            self.cleaned_data.get('bio', ''),
            field_label='About you',
        )

    def clean_phone_number(self):
        return validate_platform_phone(self.cleaned_data.get('phone_number', ''))

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise ValidationError('This email is already used on another account.')
        return email

    def save(self):
        user = self.user
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data['phone_number']
        picture = self.cleaned_data.get("profile_picture")
        if picture:
            user.profile_picture = picture
        update_fields = ['first_name', 'last_name', 'email', 'phone_number', 'updated_at']
        if picture:
            update_fields.append("profile_picture")
        user.save(update_fields=update_fields)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.bio = self.cleaned_data.get("bio", "")
        _save_profile_home(profile, self.cleaned_data)
        return user


class QashaAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["class"] = "form-control"
        self.fields["password"].widget.attrs["class"] = "form-control"
