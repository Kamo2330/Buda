from django.db import migrations


AMENITIES = [
    # Internet & tech
    ("WiFi", "fas fa-wifi", "Internet"),
    ("High-speed WiFi", "fas fa-wifi", "Internet"),
    ("Fibre internet", "fas fa-network-wired", "Internet"),
    ("Smart TV", "fas fa-tv", "Internet"),
    ("DSTV", "fas fa-satellite-dish", "Internet"),
    # Kitchen
    ("Kitchen", "fas fa-utensils", "Kitchen"),
    ("Fridge", "fas fa-snowflake", "Kitchen"),
    ("Microwave", "fas fa-microchip", "Kitchen"),
    ("Stove / oven", "fas fa-fire", "Kitchen"),
    ("Dishwasher", "fas fa-sink", "Kitchen"),
    ("Kettle & toaster", "fas fa-mug-hot", "Kitchen"),
    # Laundry
    ("Washing machine", "fas fa-tshirt", "Laundry"),
    ("Tumble dryer", "fas fa-wind", "Laundry"),
    ("Iron & ironing board", "fas fa-iron", "Laundry"),
    # Climate
    ("Air conditioning", "fas fa-snowflake", "Climate"),
    ("Heating", "fas fa-thermometer-half", "Climate"),
    ("Ceiling fan", "fas fa-fan", "Climate"),
    ("Fireplace", "fas fa-fire", "Climate"),
    # Outdoor & views
    ("Balcony", "fas fa-home", "Outdoor"),
    ("Patio", "fas fa-umbrella-beach", "Outdoor"),
    ("Garden", "fas fa-tree", "Outdoor"),
    ("Braai area", "fas fa-fire", "Outdoor"),
    ("Mountain view", "fas fa-mountain", "Outdoor"),
    ("Sea view", "fas fa-water", "Outdoor"),
    # Parking & transport
    ("Parking", "fas fa-car", "Parking"),
    ("Garage", "fas fa-warehouse", "Parking"),
    ("Secure parking", "fas fa-lock", "Parking"),
    ("Visitor parking", "fas fa-parking", "Parking"),
    # Security
    ("24-hour security", "fas fa-shield-alt", "Security"),
    ("Electric fence", "fas fa-bolt", "Security"),
    ("Alarm system", "fas fa-bell", "Security"),
    ("CCTV", "fas fa-video", "Security"),
    ("Access control", "fas fa-key", "Security"),
    # Recreation & building
    ("Swimming pool", "fas fa-swimming-pool", "Recreation"),
    ("Gym", "fas fa-dumbbell", "Recreation"),
    ("Lift / elevator", "fas fa-elevator", "Building"),
    ("Clubhouse", "fas fa-building", "Recreation"),
    ("Playground", "fas fa-child", "Recreation"),
    # Comfort & furniture
    ("Furnished", "fas fa-couch", "Comfort"),
    ("Bed linen supplied", "fas fa-bed", "Comfort"),
    ("Towels supplied", "fas fa-bath", "Comfort"),
    ("Dedicated workspace", "fas fa-laptop", "Work"),
    # Utilities & services
    ("Water included", "fas fa-faucet", "Utilities"),
    ("Electricity included", "fas fa-bolt", "Utilities"),
    ("Prepaid electricity", "fas fa-plug", "Utilities"),
    ("Cleaning service", "fas fa-broom", "Services"),
    ("Backup power", "fas fa-car-battery", "Utilities"),
    ("Solar power", "fas fa-solar-panel", "Utilities"),
    # Pets & lifestyle
    ("Pet friendly", "fas fa-paw", "Pets"),
    ("No smoking", "fas fa-smoking-ban", "House rules"),
    ("Student friendly", "fas fa-graduation-cap", "Lifestyle"),
    ("Family friendly", "fas fa-users", "Lifestyle"),
    # Accessibility
    ("Wheelchair access", "fas fa-wheelchair", "Accessibility"),
    ("Ground floor", "fas fa-stairs", "Accessibility"),
]


def seed_amenities(apps, schema_editor):
    Amenity = apps.get_model("rentals", "Amenity")
    for name, icon, category in AMENITIES:
        Amenity.objects.get_or_create(
            name=name,
            defaults={"icon": icon, "category": category},
        )


def unseed_amenities(apps, schema_editor):
    Amenity = apps.get_model("rentals", "Amenity")
    names = [row[0] for row in AMENITIES]
    Amenity.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rentals", "0008_property_featured_payment_requested_at_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_amenities, unseed_amenities),
    ]
