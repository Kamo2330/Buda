from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from rentals.models import Property, Amenity, PropertyAmenity, PropertyRule
from core.models import SiteConfiguration

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create site configuration
        site_config, created = SiteConfiguration.objects.get_or_create(
            defaults={
                'site_name': 'Qasha',
                'site_tagline': 'Find the perfect room or home with Qasha',
                'contact_email': 'contact@qasha.com',
                'contact_phone': '+1 (555) 123-4567',
                'whatsapp_number': '+1 (555) 123-4567',
                'office_address': '123 Main Street, City, State 12345',
                'facebook_url': 'https://facebook.com/qasha',
                'twitter_url': 'https://twitter.com/qasha',
                'instagram_url': 'https://instagram.com/qasha',
                'linkedin_url': 'https://linkedin.com/company/qasha',
            }
        )
        
        if created:
            self.stdout.write('✓ Site configuration created')
        else:
            self.stdout.write('✓ Site configuration already exists')
        
        # Create sample users
        users_data = [
            {
                'username': 'john_host',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Smith',
                'is_host': True,
                'is_verified': True,
            },
            {
                'username': 'sarah_host',
                'email': 'sarah@example.com',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'is_host': True,
                'is_verified': True,
            },
            {
                'username': 'mike_host',
                'email': 'mike@example.com',
                'first_name': 'Mike',
                'last_name': 'Brown',
                'is_host': True,
                'is_verified': True,
            },
            {
                'username': 'lisa_host',
                'email': 'lisa@example.com',
                'first_name': 'Lisa',
                'last_name': 'Davis',
                'is_host': True,
                'is_verified': True,
            },
        ]
        
        created_users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password('password123')
                user.save()
                created_users.append(user)
                self.stdout.write(f'✓ Created user: {user.username}')
            else:
                created_users.append(user)
                self.stdout.write(f'✓ User already exists: {user.username}')
        
        # Create amenities
        amenities_data = [
            {'name': 'WiFi', 'icon': 'fas fa-wifi', 'category': 'Internet'},
            {'name': 'Parking', 'icon': 'fas fa-car', 'category': 'Transportation'},
            {'name': 'Kitchen', 'icon': 'fas fa-utensils', 'category': 'Kitchen'},
            {'name': 'Washing Machine', 'icon': 'fas fa-tshirt', 'category': 'Laundry'},
            {'name': 'Air Conditioning', 'icon': 'fas fa-snowflake', 'category': 'Climate'},
            {'name': 'Heating', 'icon': 'fas fa-thermometer-half', 'category': 'Climate'},
            {'name': 'Pet Friendly', 'icon': 'fas fa-paw', 'category': 'Pets'},
            {'name': 'Balcony', 'icon': 'fas fa-home', 'category': 'Outdoor'},
            {'name': 'Gym', 'icon': 'fas fa-dumbbell', 'category': 'Fitness'},
            {'name': 'Swimming Pool', 'icon': 'fas fa-swimming-pool', 'category': 'Recreation'},
        ]
        
        created_amenities = []
        for amenity_data in amenities_data:
            amenity, created = Amenity.objects.get_or_create(
                name=amenity_data['name'],
                defaults=amenity_data
            )
            if created:
                created_amenities.append(amenity)
                self.stdout.write(f'✓ Created amenity: {amenity.name}')
            else:
                created_amenities.append(amenity)
        
        # Create sample properties
        properties_data = [
            {
                'title': 'Modern Studio Apartment in Downtown',
                'description': 'Beautiful modern studio apartment in the heart of downtown. Perfect for young professionals. Features a fully equipped kitchen, modern bathroom, and large windows with city views.',
                'property_type': 'studio',
                'furnishing': 'furnished',
                'lease_type': 'both',
                'address': '123 Main Street',
                'suburb': 'Downtown',
                'city': 'New York',
                'monthly_rent': 2500.00,
                'nightly_rate': 120.00,
                'deposit_amount': 2500.00,
                'utilities_included': True,
                'bedrooms': 0,
                'bathrooms': 1,
                'area_sqm': 35,
                'max_occupants': 2,
                'available_from': date.today(),
                'is_available': True,
                'is_verified': True,
                'is_published': True,
                'amenities': ['WiFi', 'Kitchen', 'Air Conditioning', 'Heating'],
                'rules': [
                    'No smoking inside the apartment',
                    'No parties or loud music after 10 PM',
                    'Pets allowed with additional deposit'
                ]
            },
            {
                'title': 'Cozy Student Room Near University',
                'description': 'Perfect student accommodation just 5 minutes walk from the university. Shared kitchen and living area with other students. Quiet neighborhood with good public transport links.',
                'property_type': 'room',
                'furnishing': 'furnished',
                'lease_type': 'monthly',
                'address': '456 College Avenue',
                'suburb': 'University District',
                'city': 'Boston',
                'monthly_rent': 800.00,
                'deposit_amount': 800.00,
                'utilities_included': True,
                'bedrooms': 1,
                'bathrooms': 1,
                'area_sqm': 15,
                'max_occupants': 1,
                'available_from': date.today() + timedelta(days=7),
                'is_available': True,
                'is_verified': True,
                'is_published': True,
                'amenities': ['WiFi', 'Kitchen', 'Washing Machine', 'Heating'],
                'rules': [
                    'Students only',
                    'No smoking',
                    'Quiet hours: 10 PM - 7 AM',
                    'Shared kitchen and bathroom'
                ]
            },
            {
                'title': 'Spacious Family House with Garden',
                'description': 'Beautiful 3-bedroom family house with a large garden. Perfect for families with children. Located in a quiet residential area with excellent schools nearby.',
                'property_type': 'house',
                'furnishing': 'unfurnished',
                'lease_type': 'monthly',
                'address': '789 Oak Street',
                'suburb': 'Greenwood',
                'city': 'Seattle',
                'monthly_rent': 3500.00,
                'deposit_amount': 3500.00,
                'utilities_included': False,
                'bedrooms': 3,
                'bathrooms': 2,
                'area_sqm': 120,
                'max_occupants': 6,
                'available_from': date.today() + timedelta(days=14),
                'is_available': True,
                'is_verified': True,
                'is_published': True,
                'amenities': ['Parking', 'Kitchen', 'Washing Machine', 'Heating', 'Pet Friendly', 'Balcony'],
                'rules': [
                    'No smoking',
                    'Pets welcome',
                    'Garden maintenance required',
                    'Minimum 12-month lease'
                ]
            },
            {
                'title': 'Luxury Apartment with City Views',
                'description': 'Stunning 2-bedroom apartment with panoramic city views. Modern amenities including gym, swimming pool, and concierge service. Perfect for short stays or monthly rentals.',
                'property_type': 'apartment',
                'furnishing': 'furnished',
                'lease_type': 'both',
                'address': '321 Skyline Boulevard',
                'suburb': 'Midtown',
                'city': 'Chicago',
                'monthly_rent': 4200.00,
                'nightly_rate': 200.00,
                'deposit_amount': 4200.00,
                'utilities_included': True,
                'bedrooms': 2,
                'bathrooms': 2,
                'area_sqm': 85,
                'max_occupants': 4,
                'available_from': date.today(),
                'is_available': True,
                'is_verified': True,
                'is_published': True,
                'amenities': ['WiFi', 'Parking', 'Kitchen', 'Air Conditioning', 'Gym', 'Swimming Pool'],
                'rules': [
                    'No smoking',
                    'No pets',
                    'Concierge service available 24/7',
                    'Access to building amenities included'
                ]
            },
            {
                'title': 'Charming Room in Shared House',
                'description': 'Cozy room in a friendly shared house. Great for students or young professionals. Shared kitchen, living room, and bathroom. Located in a vibrant neighborhood.',
                'property_type': 'room',
                'furnishing': 'semi_furnished',
                'lease_type': 'monthly',
                'address': '654 Elm Street',
                'suburb': 'Arts District',
                'city': 'Portland',
                'monthly_rent': 650.00,
                'deposit_amount': 650.00,
                'utilities_included': True,
                'bedrooms': 1,
                'bathrooms': 1,
                'area_sqm': 12,
                'max_occupants': 1,
                'available_from': date.today() + timedelta(days=3),
                'is_available': True,
                'is_verified': True,
                'is_published': True,
                'amenities': ['WiFi', 'Kitchen', 'Washing Machine', 'Heating'],
                'rules': [
                    'Shared living spaces',
                    'No smoking',
                    'Respectful of other housemates',
                    'Monthly house meetings'
                ]
            },
            {
                'title': 'Executive Short-Stay Apartment',
                'description': 'Premium furnished apartment perfect for business travelers. High-speed internet, modern amenities, and excellent location near business district.',
                'property_type': 'apartment',
                'furnishing': 'furnished',
                'lease_type': 'short_stay',
                'address': '987 Business Plaza',
                'suburb': 'Financial District',
                'city': 'San Francisco',
                'nightly_rate': 180.00,
                'deposit_amount': 500.00,
                'utilities_included': True,
                'bedrooms': 1,
                'bathrooms': 1,
                'area_sqm': 45,
                'max_occupants': 2,
                'available_from': date.today(),
                'is_available': True,
                'is_verified': True,
                'is_published': True,
                'amenities': ['WiFi', 'Kitchen', 'Air Conditioning', 'Heating', 'Gym'],
                'rules': [
                    'Business travelers preferred',
                    'No smoking',
                    'No pets',
                    'Minimum 3-night stay'
                ]
            }
        ]
        
        created_properties = []
        for i, property_data in enumerate(properties_data):
            # Get amenities and rules
            amenities = property_data.pop('amenities', [])
            rules = property_data.pop('rules', [])
            
            # Assign host
            property_data['host'] = created_users[i % len(created_users)]
            
            property_obj, created = Property.objects.get_or_create(
                title=property_data['title'],
                defaults=property_data
            )
            
            if created:
                created_properties.append(property_obj)
                self.stdout.write(f'✓ Created property: {property_obj.title}')
                
                # Add amenities
                for amenity_name in amenities:
                    try:
                        amenity = Amenity.objects.get(name=amenity_name)
                        PropertyAmenity.objects.get_or_create(
                            property=property_obj,
                            amenity=amenity
                        )
                    except Amenity.DoesNotExist:
                        pass
                
                # Add rules
                for rule_text in rules:
                    PropertyRule.objects.create(
                        property=property_obj,
                        rule_text=rule_text
                    )
            else:
                created_properties.append(property_obj)
                self.stdout.write(f'✓ Property already exists: {property_obj.title}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully created sample data:\n'
                f'  - {len(created_users)} users\n'
                f'  - {len(created_amenities)} amenities\n'
                f'  - {len(created_properties)} properties\n'
                f'  - 1 site configuration\n\n'
                f'You can now run the development server and see the populated data!'
            )
        )
