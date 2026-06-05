from django.test import SimpleTestCase

from users.address_utils import parse_sa_home_address


class AddressUtilsTests(SimpleTestCase):
    def test_three_part_address(self):
        suburb, city = parse_sa_home_address('12 Main Rd, Sandton, Johannesburg')
        self.assertEqual(suburb, 'Sandton')
        self.assertEqual(city, 'Johannesburg')

    def test_two_part_address(self):
        suburb, city = parse_sa_home_address('Sandton, Johannesburg')
        self.assertEqual(suburb, 'Sandton')
        self.assertEqual(city, 'Johannesburg')

    def test_single_place(self):
        suburb, city = parse_sa_home_address('Soweto')
        self.assertEqual(suburb, '')
        self.assertEqual(city, 'Soweto')
