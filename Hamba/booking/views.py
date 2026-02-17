import random
import string
from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .forms import (
    ExtrasForm,
    FlightSearchForm,
    PayerForm,
    PaymentMethodForm,
)
from .models import (
    Booking,
    BookingExtra,
    ExtraType,
    FlightSegment,
    Payer,
    Payment,
    Traveler,
)


def generate_booking_reference():
    """Generate a unique booking reference like HAM12345."""
    while True:
        ref = f"HAM{''.join(random.choices(string.digits, k=5))}"
        if not Booking.objects.filter(reference=ref).exists():
            return ref


def home(request):
    """Home page with flight search form."""
    if request.method == "POST":
        form = FlightSearchForm(request.POST)
        if form.is_valid():
            search_params = form.cleaned_data.copy()
            if search_params.get("departure_date"):
                search_params["departure_date"] = search_params["departure_date"].isoformat()
            if search_params.get("return_date"):
                search_params["return_date"] = search_params["return_date"].isoformat()
            request.session["search_params"] = search_params
            return redirect("booking:search_results")
    else:
        form = FlightSearchForm()

    return render(request, "booking/home.html", {"form": form})


def search_results(request):
    """Display flight options (mock data) sorted by price; POST = select option and continue."""
    search_params = request.session.get("search_params", {})
    if not search_params:
        messages.error(request, "Please search for flights first.")
        return redirect("booking:home")

    origin = search_params.get("origin", "JNB")
    destination = search_params.get("destination", "DUR")

    # Format dates for display
    display_params = search_params.copy()
    for key in ("departure_date", "return_date"):
        if display_params.get(key):
            try:
                d = date.fromisoformat(display_params[key])
                display_params[key] = d.strftime("%d %b %Y")
            except (ValueError, TypeError):
                pass

    # Mock trip options (outbound + return, sorted by total price)
    outbound_options = [
        {"airline": "LIFT", "flight_number": "GE201", "departure_time": "06:00", "arrival_time": "07:05", "price": Decimal("899.00"), "taxes": Decimal("423.00"), "cabin": "Economy"},
        {"airline": "South African Airways", "flight_number": "SA102", "departure_time": "08:30", "arrival_time": "09:35", "price": Decimal("1097.00"), "taxes": Decimal("523.00"), "cabin": "Economy"},
        {"airline": "CemAir", "flight_number": "5Z201", "departure_time": "12:15", "arrival_time": "13:20", "price": Decimal("749.00"), "taxes": Decimal("380.00"), "cabin": "Economy"},
    ]
    return_options = [
        {"airline": "South African Airways", "flight_number": "SA558", "departure_time": "14:40", "arrival_time": "15:50", "price": Decimal("0.00"), "taxes": Decimal("523.00"), "cabin": "Economy"},
        {"airline": "LIFT", "flight_number": "GE202", "departure_time": "10:00", "arrival_time": "11:05", "price": Decimal("150.00"), "taxes": Decimal("423.00"), "cabin": "Economy"},
        {"airline": "CemAir", "flight_number": "5Z202", "departure_time": "07:30", "arrival_time": "08:35", "price": Decimal("0.00"), "taxes": Decimal("380.00"), "cabin": "Economy"},
    ]

    trip_options = []
    for i, out in enumerate(outbound_options):
        ret = return_options[i % len(return_options)]
        outbound = {
            "airline": out["airline"], "flight_number": out["flight_number"],
            "origin": origin, "destination": destination,
            "departure_time": out["departure_time"], "arrival_time": out["arrival_time"],
            "price": out["price"], "taxes": out["taxes"], "cabin": out["cabin"],
        }
        ret_flight = {
            "airline": ret["airline"], "flight_number": ret["flight_number"],
            "origin": destination, "destination": origin,
            "departure_time": ret["departure_time"], "arrival_time": ret["arrival_time"],
            "price": ret["price"], "taxes": ret["taxes"], "cabin": ret["cabin"],
        }
        total_base = outbound["price"] + ret_flight["price"]
        total_taxes = outbound["taxes"] + ret_flight["taxes"]
        trip_options.append({
            "outbound": outbound,
            "return": ret_flight,
            "total_base": total_base,
            "total_taxes": total_taxes,
            "total_price": total_base + total_taxes,
        })

    trip_options.sort(key=lambda x: x["total_price"])

    if request.method == "POST":
        try:
            idx = int(request.POST.get("selected_option", 0))
        except (ValueError, TypeError):
            idx = 0
        if idx < 0 or idx >= len(trip_options):
            idx = 0
        option = trip_options[idx]
        flights = [option["outbound"], option["return"]]
        serialized = []
        for f in flights:
            serialized.append({
                **f,
                "price": str(f["price"]),
                "taxes": str(f["taxes"]),
            })
        request.session["selected_flights"] = serialized
        request.session["booking_totals"] = {
            "base_fare": str(option["total_base"]),
            "taxes": str(option["total_taxes"]),
            "extras": "0.00",
            "total": str(option["total_price"]),
        }
        return redirect("booking:booking_summary")

    return render(request, "booking/search_results.html", {
        "trip_options": trip_options,
        "search_params": display_params,
    })


def booking_summary(request):
    """Show selected flights and optional extras; POST = save extras and go to travelers."""
    selected_flights = request.session.get("selected_flights", [])
    booking_totals = request.session.get("booking_totals", {})

    if not selected_flights:
        messages.error(request, "Please select a flight first.")
        return redirect("booking:home")

    flights = []
    for f in selected_flights:
        flights.append({
            **f,
            "price": Decimal(f.get("price", "0")),
            "taxes": Decimal(f.get("taxes", "0")),
        })

    available_extras = [
        {"type": ExtraType.WHATSAPP_TICKET, "name": "Get your ticket via WhatsApp", "price": Decimal("27.00"), "description": "Get your ticket via WhatsApp"},
        {"type": ExtraType.REFUND_INSURANCE, "name": "Full refund insurance", "price": Decimal("199.00"), "description": "Full refund in event of illness, death or hospitalisation."},
        {"type": ExtraType.SMS_TICKET, "name": "Get your ticket via SMS", "price": Decimal("9.00"), "description": "Get your ticket via SMS"},
        {"type": ExtraType.DATE_CHANGE_OPTION, "name": "Date change option", "price": Decimal("339.00"), "description": "One date change without airline penalty."},
    ]

    base_fare = Decimal(booking_totals.get("base_fare", "0"))
    taxes = Decimal(booking_totals.get("taxes", "0"))

    if request.method == "POST":
        form = ExtrasForm(request.POST)
        if form.is_valid():
            extras_total = Decimal("0.00")
            selected_extras = []
            if form.cleaned_data.get("whatsapp_ticket"):
                extras_total += Decimal("27.00")
                selected_extras.append(ExtraType.WHATSAPP_TICKET)
            if form.cleaned_data.get("sms_ticket"):
                extras_total += Decimal("9.00")
                selected_extras.append(ExtraType.SMS_TICKET)
            if form.cleaned_data.get("refund_insurance"):
                extras_total += Decimal("199.00")
                selected_extras.append(ExtraType.REFUND_INSURANCE)
            if form.cleaned_data.get("date_change_option"):
                extras_total += Decimal("339.00")
                selected_extras.append(ExtraType.DATE_CHANGE_OPTION)

            total = base_fare + taxes + extras_total
            request.session["selected_extras"] = selected_extras
            request.session["booking_totals"] = {
                "base_fare": str(base_fare),
                "taxes": str(taxes),
                "extras": str(extras_total),
                "total": str(total),
            }
            return redirect("booking:traveler_details")
    else:
        form = ExtrasForm()

    totals = {
        "base_fare": base_fare,
        "taxes": taxes,
        "extras": Decimal(booking_totals.get("extras", "0")),
        "total": Decimal(booking_totals.get("total", "0")),
    }

    return render(request, "booking/booking_summary.html", {
        "flights": flights,
        "form": form,
        "available_extras": available_extras,
        "booking_totals": totals,
    })


def traveler_details(request):
    """Collect traveler details for each passenger; POST = save and go to payer."""
    selected_flights = request.session.get("selected_flights", [])
    booking_totals = request.session.get("booking_totals", {})
    search_params = request.session.get("search_params", {})

    if not selected_flights:
        messages.error(request, "Please start a new booking.")
        return redirect("booking:home")

    num_adults = search_params.get("adults", 1)
    num_children = search_params.get("children", 0)
    num_travelers = num_adults + num_children

    totals = {
        "base_fare": Decimal(booking_totals.get("base_fare", "0")),
        "taxes": Decimal(booking_totals.get("taxes", "0")),
        "extras": Decimal(booking_totals.get("extras", "0")),
        "total": Decimal(booking_totals.get("total", "0")),
    }

    if request.method == "POST":
        travelers_data = []
        errors = []
        for i in range(num_travelers):
            first_name = request.POST.get(f"traveler_{i}_first_name", "").strip()
            last_name = request.POST.get(f"traveler_{i}_last_name", "").strip()
            date_of_birth = request.POST.get(f"traveler_{i}_date_of_birth", "").strip()
            document_number = request.POST.get(f"traveler_{i}_document_number", "").strip()
            nationality = request.POST.get(f"traveler_{i}_nationality", "").strip()
            special_requests = request.POST.get(f"traveler_{i}_special_requests", "").strip()

            if not first_name:
                errors.append(f"Traveler {i + 1}: First name is required.")
            if not last_name:
                errors.append(f"Traveler {i + 1}: Last name is required.")
            if not date_of_birth:
                errors.append(f"Traveler {i + 1}: Date of birth is required.")

            travelers_data.append({
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": date_of_birth,
                "document_number": document_number,
                "nationality": nationality,
                "special_requests": special_requests,
                "is_primary_contact": i == 0,
            })

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            request.session["travelers"] = travelers_data
            return redirect("booking:payer_details")

    return render(request, "booking/traveler_details.html", {
        "num_travelers": num_travelers,
        "booking_totals": totals,
        "today": date.today(),
    })


def payer_details(request):
    """Collect payer/billing details; POST = save and go to payment method."""
    travelers = request.session.get("travelers", [])
    booking_totals = request.session.get("booking_totals", {})

    if not travelers:
        messages.error(request, "Please provide traveler details first.")
        return redirect("booking:traveler_details")

    totals = {
        "base_fare": Decimal(booking_totals.get("base_fare", "0")),
        "taxes": Decimal(booking_totals.get("taxes", "0")),
        "extras": Decimal(booking_totals.get("extras", "0")),
        "total": Decimal(booking_totals.get("total", "0")),
    }

    if request.method == "POST":
        form = PayerForm(request.POST)
        if form.is_valid():
            request.session["payer"] = form.cleaned_data
            return redirect("booking:payment_method")
    else:
        form = PayerForm()

    return render(request, "booking/payer_details.html", {
        "form": form,
        "booking_totals": totals,
    })


def payment_method(request):
    """Select payment method; POST = save and process booking."""
    payer = request.session.get("payer", {})
    booking_totals = request.session.get("booking_totals", {})

    if not payer:
        messages.error(request, "Please provide payer details first.")
        return redirect("booking:payer_details")

    totals = {
        "base_fare": Decimal(booking_totals.get("base_fare", "0")),
        "taxes": Decimal(booking_totals.get("taxes", "0")),
        "extras": Decimal(booking_totals.get("extras", "0")),
        "total": Decimal(booking_totals.get("total", "0")),
    }

    if request.method == "POST":
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            request.session["payment_method"] = form.cleaned_data["payment_method"]
            return redirect("booking:process_payment")
    else:
        form = PaymentMethodForm()

    return render(request, "booking/payment_method.html", {
        "form": form,
        "booking_totals": totals,
    })


@transaction.atomic
def process_payment(request):
    """Create booking and related objects from session; redirect to confirmation."""
    selected_flights = request.session.get("selected_flights", [])
    travelers_data = request.session.get("travelers", [])
    payer_data = request.session.get("payer", {})
    payment_method_val = request.session.get("payment_method", Payment.Method.CARD)
    selected_extras = request.session.get("selected_extras", [])
    booking_totals = request.session.get("booking_totals", {})
    search_params = request.session.get("search_params", {})

    if not all([selected_flights, travelers_data, payer_data]):
        messages.error(request, "Missing booking information. Please start over.")
        return redirect("booking:home")

    try:
        total_price = Decimal(booking_totals.get("total", "0"))
        booking = Booking.objects.create(
            reference=generate_booking_reference(),
            currency="ZAR",
            total_base_fare=Decimal(booking_totals.get("base_fare", "0")),
            total_taxes=Decimal(booking_totals.get("taxes", "0")),
            total_extras=Decimal(booking_totals.get("extras", "0")),
            total_price=total_price,
            status=Booking.Status.CONFIRMED,
            contact_email=payer_data.get("email", ""),
            contact_phone=payer_data.get("phone", ""),
            source="web",
        )

        for i, t in enumerate(travelers_data):
            dob = None
            if t.get("date_of_birth"):
                try:
                    dob = datetime.strptime(t["date_of_birth"], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    pass
            Traveler.objects.create(
                booking=booking,
                first_name=t["first_name"],
                last_name=t["last_name"],
                date_of_birth=dob,
                document_number=t.get("document_number", ""),
                nationality=t.get("nationality", ""),
                is_primary_contact=t.get("is_primary_contact", i == 0),
                special_requests=t.get("special_requests", ""),
            )

        Payer.objects.create(
            booking=booking,
            first_name=payer_data["first_name"],
            last_name=payer_data["last_name"],
            email=payer_data["email"],
            phone=payer_data.get("phone", ""),
            billing_address_line1=payer_data.get("billing_address_line1", ""),
            billing_address_line2=payer_data.get("billing_address_line2", ""),
            billing_city=payer_data.get("billing_city", ""),
            billing_postcode=payer_data.get("billing_postcode", ""),
            billing_country=payer_data.get("billing_country", ""),
        )

        dep_date = datetime(2025, 12, 20, 6, 0)
        if search_params.get("departure_date"):
            try:
                dep_date = datetime.strptime(search_params["departure_date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        return_date = None
        if search_params.get("return_date"):
            try:
                return_date = datetime.strptime(search_params["return_date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        for i, flight in enumerate(selected_flights):
            origin = flight.get("origin", "JNB")
            dest = flight.get("destination", "DUR")
            if i == 0:
                dep_dt = dep_date.replace(hour=6, minute=0)
                arr_dt = dep_date.replace(hour=7, minute=5)
                direction = "OUTBOUND"
            else:
                rd = return_date or dep_date
                dep_dt = rd.replace(hour=14, minute=40)
                arr_dt = rd.replace(hour=15, minute=50)
                direction = "RETURN"

            FlightSegment.objects.create(
                booking=booking,
                airline_name=flight.get("airline", ""),
                flight_number=flight.get("flight_number", ""),
                origin_airport_code=origin,
                origin_airport_name=f"{origin} Airport",
                destination_airport_code=dest,
                destination_airport_name=f"{dest} Airport",
                departure_datetime=dep_dt,
                arrival_datetime=arr_dt,
                cabin_class=flight.get("cabin", "ECONOMY"),
                hand_baggage_kg=Decimal("7.0"),
                checked_baggage_kg=Decimal("23.0") if i == 1 else None,
                direction=direction,
            )

        extra_prices = {
            ExtraType.WHATSAPP_TICKET: Decimal("27.00"),
            ExtraType.SMS_TICKET: Decimal("9.00"),
            ExtraType.REFUND_INSURANCE: Decimal("199.00"),
            ExtraType.DATE_CHANGE_OPTION: Decimal("339.00"),
        }
        extra_descriptions = {
            ExtraType.WHATSAPP_TICKET: "Get your ticket via WhatsApp",
            ExtraType.SMS_TICKET: "Get your ticket via SMS",
            ExtraType.REFUND_INSURANCE: "Full refund insurance (illness/death/hospitalisation).",
            ExtraType.DATE_CHANGE_OPTION: "One date change without airline penalty.",
        }
        for extra_type in selected_extras:
            BookingExtra.objects.create(
                booking=booking,
                extra_type=extra_type,
                description=extra_descriptions.get(extra_type, ""),
                price=extra_prices.get(extra_type, Decimal("0.00")),
                currency="ZAR",
                applies_to_all_travelers=True,
            )

        Payment.objects.create(
            booking=booking,
            amount=total_price,
            currency="ZAR",
            method=payment_method_val,
            status=Payment.Status.SUCCESS,
            provider_reference=f"TXN{''.join(random.choices(string.digits, k=10))}",
        )

        for key in ["selected_flights", "travelers", "payer", "payment_method", "selected_extras", "booking_totals", "search_params"]:
            request.session.pop(key, None)

        return redirect("booking:confirmation", booking_ref=booking.reference)

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("booking:payment_method")


def confirmation(request, booking_ref):
    """Show booking confirmation."""
    booking = get_object_or_404(Booking, reference=booking_ref)
    return render(request, "booking/confirmation.html", {"booking": booking})


@require_GET
def airport_search(request):
    """JSON endpoint for airport autocomplete."""
    from django.db.models import Q
    from .models import Airport

    query = (request.GET.get("q") or "").strip()
    if not query:
        return JsonResponse([], safe=False)

    q = query.lower()
    airports = (
        Airport.objects.filter(is_active=True)
        .filter(
            Q(iata_code__icontains=q)
            | Q(city__icontains=q)
            | Q(name__icontains=q)
            | Q(country__icontains=q)
        )
        .order_by("city", "name")[:10]
    )
    data = [
        {"code": a.iata_code, "city": a.city, "name": a.name, "country": a.country}
        for a in airports
    ]
    return JsonResponse(data, safe=False)
