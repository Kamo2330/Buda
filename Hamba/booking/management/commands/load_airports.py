"""
Load airports from OurAirports CSV (data/airports.csv).
Usage: python manage.py load_airports [--clear] [--path PATH]
"""
import csv
import os

from django.core.management.base import BaseCommand

from booking.models import Airport


# ISO 3166-1 alpha-2 to country name (common + all that appear in OurAirports)
COUNTRY_NAMES = {
    "ZA": "South Africa", "US": "United States", "GB": "United Kingdom", "DE": "Germany",
    "FR": "France", "AU": "Australia", "CA": "Canada", "IN": "India", "CN": "China", "JP": "Japan",
    "BR": "Brazil", "MX": "Mexico", "ES": "Spain", "IT": "Italy", "NL": "Netherlands", "RU": "Russia",
    "KR": "South Korea", "AE": "United Arab Emirates", "SA": "Saudi Arabia", "SG": "Singapore",
    "HK": "Hong Kong", "TH": "Thailand", "MY": "Malaysia", "ID": "Indonesia", "PH": "Philippines",
    "VN": "Vietnam", "PL": "Poland", "TR": "Turkey", "EG": "Egypt", "NG": "Nigeria", "KE": "Kenya",
    "GH": "Ghana", "MA": "Morocco", "TZ": "Tanzania", "ET": "Ethiopia", "ZA": "South Africa",
    "BW": "Botswana", "NA": "Namibia", "ZW": "Zimbabwe", "MZ": "Mozambique", "LS": "Lesotho",
    "SZ": "Eswatini", "PT": "Portugal", "GR": "Greece", "SE": "Sweden", "NO": "Norway",
    "FI": "Finland", "DK": "Denmark", "IE": "Ireland", "CH": "Switzerland", "AT": "Austria",
    "BE": "Belgium", "CZ": "Czech Republic", "RO": "Romania", "HU": "Hungary", "IL": "Israel",
    "QA": "Qatar", "KW": "Kuwait", "BH": "Bahrain", "OM": "Oman", "JO": "Jordan", "LB": "Lebanon",
    "PK": "Pakistan", "BD": "Bangladesh", "LK": "Sri Lanka", "NZ": "New Zealand", "AR": "Argentina",
    "CL": "Chile", "CO": "Colombia", "PE": "Peru", "VE": "Venezuela", "EC": "Ecuador",
    "UA": "Ukraine", "BY": "Belarus", "KZ": "Kazakhstan",
    "TN": "Tunisia", "LY": "Libya", "SD": "Sudan", "SN": "Senegal", "CI": "Côte d'Ivoire",
    "CM": "Cameroon", "UG": "Uganda", "MU": "Mauritius", "RE": "Réunion",
    "CY": "Cyprus", "MT": "Malta", "LU": "Luxembourg", "SK": "Slovakia", "BG": "Bulgaria",
    "HR": "Croatia", "RS": "Serbia", "SI": "Slovenia", "LT": "Lithuania", "LV": "Latvia",
    "EE": "Estonia", "IS": "Iceland", "PR": "Puerto Rico", "DO": "Dominican Republic",
    "JM": "Jamaica", "TT": "Trinidad and Tobago", "BS": "Bahamas", "CU": "Cuba",
    "PA": "Panama", "CR": "Costa Rica", "GT": "Guatemala", "HN": "Honduras", "SV": "El Salvador",
    "NI": "Nicaragua", "EC": "Ecuador", "PY": "Paraguay", "UY": "Uruguay", "BO": "Bolivia",
    "IR": "Iran", "IQ": "Iraq", "SY": "Syria", "YE": "Yemen", "AF": "Afghanistan",
    "NP": "Nepal", "MM": "Myanmar", "KH": "Cambodia", "LA": "Laos", "MN": "Mongolia",
    "TW": "Taiwan", "LK": "Sri Lanka", "MV": "Maldives", "NP": "Nepal",
    "AL": "Albania", "BA": "Bosnia and Herzegovina", "MK": "North Macedonia", "ME": "Montenegro",
    "GE": "Georgia", "AM": "Armenia", "AZ": "Azerbaijan", "UZ": "Uzbekistan", "TM": "Turkmenistan",
    "TJ": "Tajikistan", "KG": "Kyrgyzstan", "PG": "Papua New Guinea", "FJ": "Fiji",
    "NC": "New Caledonia", "PF": "French Polynesia", "DZ": "Algeria", "AO": "Angola",
    "ZM": "Zambia", "MW": "Malawi", "MG": "Madagascar", "SC": "Seychelles", "CV": "Cape Verde",
    "GA": "Gabon", "CG": "Republic of the Congo", "CD": "Democratic Republic of the Congo",
    "NE": "Niger", "ML": "Mali", "BF": "Burkina Faso", "GN": "Guinea", "GM": "Gambia",
    "LR": "Liberia", "SL": "Sierra Leone", "TG": "Togo", "BJ": "Benin", "RW": "Rwanda",
    "BI": "Burundi", "SO": "Somalia", "DJ": "Djibouti", "ER": "Eritrea", "SS": "South Sudan",
    "GY": "Guyana", "SR": "Suriname", "BZ": "Belize", "HT": "Haiti", "BB": "Barbados",
    "GD": "Grenada", "LC": "Saint Lucia", "VC": "Saint Vincent and the Grenadines",
    "DM": "Dominica", "AG": "Antigua and Barbuda", "KN": "Saint Kitts and Nevis",
    "KY": "Cayman Islands", "BM": "Bermuda", "GL": "Greenland", "FO": "Faroe Islands",
    "MC": "Monaco", "AD": "Andorra", "SM": "San Marino", "VA": "Vatican City", "XK": "Kosovo",
    "FK": "Falkland Islands", "GF": "French Guiana", "MQ": "Martinique", "GP": "Guadeloupe",
    "AW": "Aruba", "CW": "Curaçao", "BQ": "Caribbean Netherlands", "SX": "Sint Maarten",
    "VI": "U.S. Virgin Islands", "VG": "British Virgin Islands", "TC": "Turks and Caicos",
    "JE": "Jersey", "GG": "Guernsey", "IM": "Isle of Man", "GI": "Gibraltar", "AX": "Åland Islands",
}


def get_country_name(iso_code):
    if not iso_code or len(iso_code) != 2:
        return iso_code or "Unknown"
    return COUNTRY_NAMES.get(iso_code.upper(), iso_code.upper())


class Command(BaseCommand):
    help = "Load airports from OurAirports CSV (data/airports.csv)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing airports before loading.",
        )
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Path to airports.csv (default: data/airports.csv under project root).",
        )

    def handle(self, *args, **options):
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        path = options.get("path") or os.path.join(project_root, "data", "airports.csv")
        if not os.path.isfile(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        if options["clear"]:
            n = Airport.objects.count()
            Airport.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {n} airports."))

        created = 0
        updated = 0
        preferred_types = {"large_airport", "medium_airport"}
        with open(path, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            iata = (row.get("iata_code") or "").strip()
            if not iata or len(iata) > 3:
                continue
            name = (row.get("name") or "").strip()[:255]
            municipality = (row.get("municipality") or "").strip()[:100]
            iso_country = (row.get("iso_country") or "").strip()
            country = get_country_name(iso_country)[:100]
            if not name:
                continue
            code = iata.upper() if len(iata) == 3 else iata
            row_type = (row.get("type") or "").strip()
            try:
                existing = Airport.objects.get(iata_code=code)
                if row_type not in preferred_types:
                    continue
            except Airport.DoesNotExist:
                pass
            obj, was_created = Airport.objects.update_or_create(
                iata_code=code,
                defaults={
                    "name": name,
                    "city": municipality or name[:100],
                    "country": country,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Done. Created {created}, updated {updated} airports.")
        )
