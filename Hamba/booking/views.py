import random
import string
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Booking, Traveler, Payer, BookingExtra, ExtraType, FlightSegment, Payment
from .forms import (
    FlightSearchForm, TravelerForm, PayerForm, ExtrasForm, PaymentMethodForm
)


def generate_booking_reference():
    """Generate a unique booking reference like HAM12345."""
    while True:
        ref = f"HAM{''.join(random.choices(string.digits, k=5))}"
        if not Booking.objects.filter(reference=ref).exists():
            return ref


def home(request):
    """Home page with search form."""
    if request.method == 'POST':
        form = FlightSearchForm(request.POST)
        if form.is_valid():
            # Store search params in session for later use
            request.session['search_params'] = form.cleaned_data
            return redirect('booking:search_results')
    else:
        form = FlightSearchForm()
    
    return render(request, 'booking/home.html', {'form': form})


def search_results(request):
    """Display flight search results (mock data for now)."""
    search_params = request.session.get('search_params', {})
    
    # Mock flight results - in production, this would query an API or database
    mock_flights = [
        {
            'airline': 'LIFT',
            'flight_number': 'GE201',
            'origin': search_params.get('origin', 'JNB'),
            'destination': search_params.get('destination', 'DUR'),
            'departure_time': '06:00',
            'arrival_time': '07:05',
            'price': Decimal('1097.00'),
            'taxes': Decimal('523.00'),
            'cabin': 'Economy'
        },
        {
            'airline': 'South African Airways',
            'flight_number': 'SA558',
            'origin': search_params.get('destination', 'DUR'),
            'destination': search_params.get('origin', 'JNB'),
            'departure_time': '14:40',
            'arrival_time': '15:50',
            'price': Decimal('0.00'),  # Return leg included
            'taxes': Decimal('523.00'),
            'cabin': 'Economy'
        }
    ]
    
    # Calculate totals
    total_base = sum(f['price'] for f in mock_flights) or Decimal('1097.00')
    total_taxes = sum(f['taxes'] for f in mock_flights)
    total_price = total_base + total_taxes
    
    if request.method == 'POST':
        # User selected a flight, proceed to booking summary
        request.session['selected_flights'] = mock_flights
        request.session['booking_totals'] = {
            'base_fare': str(total_base),
            'taxes': str(total_taxes),
            'extras': '0.00',
            'total': str(total_price)
        }
        return redirect('booking:booking_summary')
    
    return render(request, 'booking/search_results.html', {
        'flights': mock_flights,
        'search_params': search_params,
        'total_base': total_base,
        'total_taxes': total_taxes,
        'total_price': total_price
    })


def booking_summary(request):
    """Booking summary page with optional extras."""
    selected_flights = request.session.get('selected_flights', [])
    booking_totals = request.session.get('booking_totals', {})
    
    if not selected_flights:
        messages.error(request, 'Please select a flight first.')
        return redirect('booking:home')
    
    # Define available extras with prices
    available_extras = [
        {
            'type': ExtraType.WHATSAPP_TICKET,
            'name': 'Get your ticket via WHATSAPP',
            'price': Decimal('27.00'),
            'description': 'Get your ticket via WHATSAPP'
        },
        {
            'type': ExtraType.REFUND_INSURANCE,
            'name': 'Full refund insurance',
            'price': Decimal('199.00'),
            'description': 'Receive a full refund of airfare and taxes in the event of sudden illness, death or hospitalisation of yourself or a close relative, prior to departure.'
        },
        {
            'type': ExtraType.SMS_TICKET,
            'name': 'Get your ticket via SMS',
            'price': Decimal('9.00'),
            'description': 'Get your ticket via SMS'
        },
        {
            'type': ExtraType.DATE_CHANGE_OPTION,
            'name': 'Date change option',
            'price': Decimal('339.00'),
            'description': 'Make one date change to your flight without paying the airline penalty fee. You only pay the difference in fare and taxes if applicable. Valid up to 24 hours prior to departure of the original ticket.'
        }
    ]
    
    if request.method == 'POST':
        form = ExtrasForm(request.POST)
        if form.is_valid():
            # Calculate extras total
            extras_total = Decimal('0.00')
            selected_extras = []
            
            if form.cleaned_data.get('whatsapp_ticket'):
                extras_total += Decimal('27.00')
                selected_extras.append(ExtraType.WHATSAPP_TICKET)
            if form.cleaned_data.get('sms_ticket'):
                extras_total += Decimal('9.00')
                selected_extras.append(ExtraType.SMS_TICKET)
            if form.cleaned_data.get('refund_insurance'):
                extras_total += Decimal('199.00')
                selected_extras.append(ExtraType.REFUND_INSURANCE)
            if form.cleaned_data.get('date_change_option'):
                extras_total += Decimal('339.00')
                selected_extras.append(ExtraType.DATE_CHANGE_OPTION)
            
            # Update totals in session
            base_fare = Decimal(booking_totals.get('base_fare', '0'))
            taxes = Decimal(booking_totals.get('taxes', '0'))
            total = base_fare + taxes + extras_total
            
            request.session['selected_extras'] = selected_extras
            request.session['booking_totals'] = {
                'base_fare': str(base_fare),
                'taxes': str(taxes),
                'extras': str(extras_total),
                'total': str(total)
            }
            
            return redirect('booking:traveler_details')
    else:
        form = ExtrasForm()
    
    return render(request, 'booking/booking_summary.html', {
        'flights': selected_flights,
        'form': form,
        'available_extras': available_extras,
        'booking_totals': booking_totals
    })


def traveler_details(request):
    """Collect traveler information."""
    selected_flights = request.session.get('selected_flights', [])
    booking_totals = request.session.get('booking_totals', {})
    
    if not selected_flights:
        messages.error(request, 'Please start a new booking.')
        return redirect('booking:home')
    
    # Get number of travelers from search params
    search_params = request.session.get('search_params', {})
    num_adults = search_params.get('adults', 1)
    num_children = search_params.get('children', 0)
    num_travelers = num_adults + num_children
    
    if request.method == 'POST':
        travelers_data = []
        for i in range(num_travelers):
            traveler = {
                'first_name': request.POST.get(f'traveler_{i}_first_name', ''),
                'last_name': request.POST.get(f'traveler_{i}_last_name', ''),
                'date_of_birth': request.POST.get(f'traveler_{i}_date_of_birth', ''),
                'document_number': request.POST.get(f'traveler_{i}_document_number', ''),
                'nationality': request.POST.get(f'traveler_{i}_nationality', ''),
                'special_requests': request.POST.get(f'traveler_{i}_special_requests', ''),
                'is_primary_contact': i == 0  # First traveler is primary
            }
            travelers_data.append(traveler)
        
        # Validate all travelers have required fields
        valid = all(
            t['first_name'] and t['last_name'] and t['date_of_birth']
            for t in travelers_data
        )
        
        if valid:
            request.session['travelers'] = travelers_data
            return redirect('booking:payer_details')
        else:
            messages.error(request, 'Please fill in all required fields for all travelers.')
    
    return render(request, 'booking/traveler_details.html', {
        'num_travelers': num_travelers,
        'booking_totals': booking_totals
    })


def payer_details(request):
    """Collect payer/billing information."""
    travelers = request.session.get('travelers', [])
    booking_totals = request.session.get('booking_totals', {})
    
    if not travelers:
        messages.error(request, 'Please provide traveler details first.')
        return redirect('booking:traveler_details')
    
    if request.method == 'POST':
        form = PayerForm(request.POST)
        if form.is_valid():
            request.session['payer'] = form.cleaned_data
            return redirect('booking:payment_method')
    else:
        form = PayerForm()
    
    return render(request, 'booking/payer_details.html', {
        'form': form,
        'booking_totals': booking_totals
    })


def payment_method(request):
    """Select payment method."""
    payer = request.session.get('payer', {})
    booking_totals = request.session.get('booking_totals', {})
    
    if not payer:
        messages.error(request, 'Please provide payer details first.')
        return redirect('booking:payer_details')
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            request.session['payment_method'] = form.cleaned_data['payment_method']
            return redirect('booking:process_payment')
    else:
        form = PaymentMethodForm()
    
    return render(request, 'booking/payment_method.html', {
        'form': form,
        'booking_totals': booking_totals
    })


@transaction.atomic
def process_payment(request):
    """Process payment and create booking."""
    selected_flights = request.session.get('selected_flights', [])
    travelers_data = request.session.get('travelers', [])
    payer_data = request.session.get('payer', {})
    payment_method = request.session.get('payment_method', Payment.Method.CARD)
    selected_extras = request.session.get('selected_extras', [])
    booking_totals = request.session.get('booking_totals', {})
    search_params = request.session.get('search_params', {})
    
    if not all([selected_flights, travelers_data, payer_data]):
        messages.error(request, 'Missing booking information. Please start over.')
        return redirect('booking:home')
    
    try:
        # Create booking
        booking = Booking.objects.create(
            reference=generate_booking_reference(),
            currency='ZAR',
            total_base_fare=Decimal(booking_totals.get('base_fare', '0')),
            total_taxes=Decimal(booking_totals.get('taxes', '0')),
            total_extras=Decimal(booking_totals.get('extras', '0')),
            total_price=Decimal(booking_totals.get('total', '0')),
            status=Booking.Status.CONFIRMED,
            contact_email=payer_data.get('email', ''),
            contact_phone=payer_data.get('phone', ''),
            source='web'
        )
        
        # Create travelers
        for i, traveler_data in enumerate(travelers_data):
            Traveler.objects.create(
                booking=booking,
                first_name=traveler_data['first_name'],
                last_name=traveler_data['last_name'],
                date_of_birth=datetime.strptime(traveler_data['date_of_birth'], '%Y-%m-%d').date() if traveler_data.get('date_of_birth') else None,
                document_number=traveler_data.get('document_number', ''),
                nationality=traveler_data.get('nationality', ''),
                is_primary_contact=traveler_data.get('is_primary_contact', i == 0),
                special_requests=traveler_data.get('special_requests', '')
            )
        
        # Create payer
        Payer.objects.create(
            booking=booking,
            first_name=payer_data['first_name'],
            last_name=payer_data['last_name'],
            email=payer_data['email'],
            phone=payer_data.get('phone', ''),
            billing_address_line1=payer_data.get('billing_address_line1', ''),
            billing_address_line2=payer_data.get('billing_address_line2', ''),
            billing_city=payer_data.get('billing_city', ''),
            billing_postcode=payer_data.get('billing_postcode', ''),
            billing_country=payer_data.get('billing_country', '')
        )
        
        # Create flight segments
        try:
            departure_date = datetime.strptime(search_params.get('departure_date', '2024-12-20'), '%Y-%m-%d')
        except (ValueError, TypeError):
            departure_date = datetime(2024, 12, 20, 6, 0)
        
        return_date = None
        if search_params.get('return_date'):
            try:
                return_date = datetime.strptime(search_params.get('return_date'), '%Y-%m-%d')
            except (ValueError, TypeError):
                return_date = None
        
        for i, flight in enumerate(selected_flights):
            if i == 0:  # Outbound
                dep_dt = departure_date.replace(hour=6, minute=0)
                arr_dt = departure_date.replace(hour=7, minute=5)
                direction = 'OUTBOUND'
            else:  # Return
                dep_dt = return_date.replace(hour=14, minute=40) if return_date else departure_date.replace(hour=14, minute=40)
                arr_dt = return_date.replace(hour=15, minute=50) if return_date else departure_date.replace(hour=15, minute=50)
                direction = 'RETURN'
            
            FlightSegment.objects.create(
                booking=booking,
                airline_name=flight['airline'],
                flight_number=flight['flight_number'],
                origin_airport_code=flight['origin'],
                origin_airport_name=f"{flight['origin']} Airport",
                destination_airport_code=flight['destination'],
                destination_airport_name=f"{flight['destination']} Airport",
                departure_datetime=dep_dt,
                arrival_datetime=arr_dt,
                cabin_class=flight.get('cabin', 'ECONOMY'),
                hand_baggage_kg=Decimal('7.0'),
                checked_baggage_kg=Decimal('23.0') if i == 1 else None,
                direction=direction
            )
        
        # Create extras
        extra_prices = {
            ExtraType.WHATSAPP_TICKET: Decimal('27.00'),
            ExtraType.SMS_TICKET: Decimal('9.00'),
            ExtraType.REFUND_INSURANCE: Decimal('199.00'),
            ExtraType.DATE_CHANGE_OPTION: Decimal('339.00')
        }
        
        extra_descriptions = {
            ExtraType.WHATSAPP_TICKET: 'Get your ticket via WHATSAPP',
            ExtraType.SMS_TICKET: 'Get your ticket via SMS',
            ExtraType.REFUND_INSURANCE: 'Receive a full refund of airfare and taxes in the event of sudden illness, death or hospitalisation of yourself or a close relative, prior to departure.',
            ExtraType.DATE_CHANGE_OPTION: 'Make one date change to your flight without paying the airline penalty fee. You only pay the difference in fare and taxes if applicable. Valid up to 24 hours prior to departure of the original ticket.'
        }
        
        for extra_type in selected_extras:
            BookingExtra.objects.create(
                booking=booking,
                extra_type=extra_type,
                description=extra_descriptions.get(extra_type, ''),
                price=extra_prices.get(extra_type, Decimal('0.00')),
                currency='ZAR',
                applies_to_all_travelers=True
            )
        
        # Create payment record
        Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            currency='ZAR',
            method=payment_method,
            status=Payment.Status.SUCCESS,
            provider_reference=f"TXN{''.join(random.choices(string.digits, k=10))}"
        )
        
        # Clear session data
        for key in ['selected_flights', 'travelers', 'payer', 'payment_method', 'selected_extras', 'booking_totals', 'search_params']:
            request.session.pop(key, None)
        
        return redirect('booking:confirmation', booking_ref=booking.reference)
    
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('booking:payment_method')


def confirmation(request, booking_ref):
    """Booking confirmation page."""
    booking = get_object_or_404(Booking, reference=booking_ref)
    
    return render(request, 'booking/confirmation.html', {
        'booking': booking
    })

