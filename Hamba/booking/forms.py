from django import forms
from django.forms import inlineformset_factory
from .models import Booking, Traveler, Payer, BookingExtra, ExtraType, FlightSegment, Payment


class FlightSearchForm(forms.Form):
    """Form for searching flights."""
    trip_type = forms.ChoiceField(
        choices=[('oneway', 'One Way'), ('return', 'Return')],
        widget=forms.RadioSelect(attrs={'class': 'trip-type-radio'}),
        initial='return'
    )
    origin = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'From (city or airport)',
            'autocomplete': 'off'
        })
    )
    destination = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'To (city or airport)',
            'autocomplete': 'off'
        })
    )
    departure_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control smart-datepicker',
            'type': 'date'
        })
    )
    return_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control smart-datepicker',
            'type': 'date'
        })
    )
    adults = forms.IntegerField(
        min_value=1,
        max_value=9,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '9'
        })
    )
    children = forms.IntegerField(
        min_value=0,
        max_value=9,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '9'
        })
    )


class TravelerForm(forms.ModelForm):
    """Form for traveler details."""
    class Meta:
        model = Traveler
        fields = ['first_name', 'last_name', 'date_of_birth', 'document_number', 'nationality', 'special_requests']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'document_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID / Passport number'
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nationality'
            }),
            'special_requests': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Special requests (optional)'
            })
        }


TravelerFormSet = inlineformset_factory(
    Booking,
    Traveler,
    form=TravelerForm,
    extra=1,
    can_delete=False
)


class PayerForm(forms.ModelForm):
    """Form for payer/billing details."""
    class Meta:
        model = Payer
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_postcode', 'billing_country'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'billing_address_line1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Address line 1'
            }),
            'billing_address_line2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Address line 2 (optional)'
            }),
            'billing_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'billing_postcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal code'
            }),
            'billing_country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            })
        }


class ExtrasForm(forms.Form):
    """Form for selecting optional extras."""
    whatsapp_ticket = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'extra-checkbox'})
    )
    sms_ticket = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'extra-checkbox'})
    )
    refund_insurance = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'extra-checkbox'})
    )
    date_change_option = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'extra-checkbox'})
    )


class PaymentMethodForm(forms.Form):
    """Form for selecting payment method."""
    payment_method = forms.ChoiceField(
        choices=Payment.Method.choices,
        widget=forms.RadioSelect(attrs={'class': 'payment-method-radio'}),
        initial=Payment.Method.CARD
    )









