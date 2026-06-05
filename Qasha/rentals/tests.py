from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .booking_utils import (
    dates_overlap,
    property_has_confirmed_tenant,
    validate_booking_dates,
)
from .models import Booking, Property

User = get_user_model()


class BookingUtilsTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username='host1', email='h@example.com', password='pass12345'
        )
        self.guest = User.objects.create_user(
            username='guest1', email='g@example.com', password='pass12345'
        )
        self.property = Property.objects.create(
            host=self.host,
            title='Room · Test, City',
            description='Test',
            property_type='room',
            furnishing='furnished',
            lease_type='monthly',
            address='1 Test St',
            suburb='Test',
            city='City',
            monthly_rent=Decimal('5000'),
            deposit_amount=Decimal('0'),
            available_from=date.today(),
            bedrooms=1,
            bathrooms=1,
            is_published=True,
            is_available=True,
        )

    def test_dates_overlap(self):
        a = date(2026, 6, 1)
        b = date(2026, 6, 10)
        c = date(2026, 6, 5)
        d = date(2026, 6, 15)
        self.assertTrue(dates_overlap(a, b, c, d))
        self.assertFalse(dates_overlap(a, b, d, d + timedelta(days=5)))

    def test_confirmed_tenant_includes_accepted(self):
        Booking.objects.create(
            property=self.property,
            guest=self.guest,
            check_in_date=date.today() + timedelta(days=7),
            check_out_date=date.today() + timedelta(days=30),
            total_amount=Decimal('0'),
            status='accepted',
        )
        self.property.is_occupied = False
        self.property.save(update_fields=['is_occupied'])
        self.assertTrue(property_has_confirmed_tenant(self.property))

    def test_accepted_booking_excludes_self_from_other_tenant_check(self):
        """Accepting must not treat this pending booking as an existing tenant."""
        booking = Booking.objects.create(
            property=self.property,
            guest=self.guest,
            check_in_date=date.today() + timedelta(days=7),
            check_out_date=date.today() + timedelta(days=30),
            total_amount=Decimal('0'),
            status='pending',
            payment_on_file=True,
        )
        other_holds = Booking.objects.filter(
            property=self.property,
            status__in=('accepted', 'secured'),
        ).exclude(pk=booking.pk)
        self.assertFalse(other_holds.exists())

    def test_validate_available_from(self):
        self.property.available_from = date.today() + timedelta(days=14)
        self.property.save(update_fields=['available_from'])
        with self.assertRaises(ValidationError):
            validate_booking_dates(
                self.property,
                date.today() + timedelta(days=1),
                date.today() + timedelta(days=5),
            )
