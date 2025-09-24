from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from menu.models import Club, Table, Category, Product


class Command(BaseCommand):
    help = 'Populate the database with sample data for testing'

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write('Creating sample data...')
            
            # Create a sample club
            club, created = Club.objects.get_or_create(
                slug='test-club',
                defaults={
                    'name': 'Buda Test Club',
                    'description': 'A test club for the Buda ordering system',
                    'address': '123 Test Street, Cape Town, South Africa',
                    'phone': '+27 21 123 4567',
                    'email': 'info@budatest.co.za',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'Created club: {club.name}')
            else:
                self.stdout.write(f'Using existing club: {club.name}')
            
            # Create tables
            tables_data = [
                {'number': '1', 'is_active': True},
                {'number': '2', 'is_active': True},
                {'number': '3', 'is_active': True},
                {'number': '4', 'is_active': True},
                {'number': '5', 'is_active': True},
                {'number': '6', 'is_active': True},
                {'number': '7', 'is_active': True},
                {'number': '8', 'is_active': True},
                {'number': '9', 'is_active': True},
                {'number': '10', 'is_active': True},
                {'number': 'VIP1', 'is_active': True},
                {'number': 'VIP2', 'is_active': True},
            ]
            
            for table_data in tables_data:
                table, created = Table.objects.get_or_create(
                    club=club,
                    number=table_data['number'],
                    defaults=table_data
                )
                if created:
                    self.stdout.write(f'Created table: {table.number}')
            
            # Create categories
            categories_data = [
                {'name': 'Beers', 'slug': 'beers', 'icon': '🍺', 'display_order': 1},
                {'name': 'Ciders', 'slug': 'ciders', 'icon': '🍎', 'display_order': 2},
                {'name': 'Spirits', 'slug': 'spirits', 'icon': '🥃', 'display_order': 3},
                {'name': 'Mixers', 'slug': 'mixers', 'icon': '🥤', 'display_order': 4},
                {'name': 'Snacks', 'slug': 'snacks', 'icon': '🍿', 'display_order': 5},
            ]
            
            for cat_data in categories_data:
                category, created = Category.objects.get_or_create(
                    slug=cat_data['slug'],
                    defaults=cat_data
                )
                if created:
                    self.stdout.write(f'Created category: {category.name}')
            
            # Create products
            products_data = [
                # Beers
                {'name': 'Castle Lager', 'category': 'beers', 'price': Decimal('25.00'), 'description': 'South Africa\'s most popular beer'},
                {'name': 'Castle Lite', 'category': 'beers', 'price': Decimal('26.00'), 'description': 'Light and refreshing'},
                {'name': 'Black Label', 'category': 'beers', 'price': Decimal('28.00'), 'description': 'Premium lager'},
                {'name': 'Heineken', 'category': 'beers', 'price': Decimal('32.00'), 'description': 'Imported premium beer'},
                {'name': 'Corona Extra', 'category': 'beers', 'price': Decimal('35.00'), 'description': 'Mexican lager with lime'},
                {'name': 'Stella Artois', 'category': 'beers', 'price': Decimal('30.00'), 'description': 'Belgian premium lager'},
                
                # Ciders
                {'name': 'Savannah Dry', 'category': 'ciders', 'price': Decimal('28.00'), 'description': 'Crisp and dry cider'},
                {'name': 'Savannah Light', 'category': 'ciders', 'price': Decimal('29.00'), 'description': 'Light and refreshing cider'},
                {'name': 'Hunters Dry', 'category': 'ciders', 'price': Decimal('26.00'), 'description': 'Classic dry cider'},
                {'name': 'Strongbow', 'category': 'ciders', 'price': Decimal('30.00'), 'description': 'English cider'},
                
                # Spirits
                {'name': 'Vodka (Single)', 'category': 'spirits', 'price': Decimal('45.00'), 'description': 'Premium vodka shot'},
                {'name': 'Whiskey (Single)', 'category': 'spirits', 'price': Decimal('50.00'), 'description': 'Premium whiskey shot'},
                {'name': 'Gin (Single)', 'category': 'spirits', 'price': Decimal('48.00'), 'description': 'Premium gin shot'},
                {'name': 'Rum (Single)', 'category': 'spirits', 'price': Decimal('46.00'), 'description': 'Premium rum shot'},
                
                # Mixers
                {'name': 'Coke', 'category': 'mixers', 'price': Decimal('15.00'), 'description': 'Coca Cola'},
                {'name': 'Sprite', 'category': 'mixers', 'price': Decimal('15.00'), 'description': 'Lemon-lime soda'},
                {'name': 'Tonic Water', 'category': 'mixers', 'price': Decimal('18.00'), 'description': 'Premium tonic water'},
                {'name': 'Orange Juice', 'category': 'mixers', 'price': Decimal('20.00'), 'description': 'Fresh orange juice'},
                {'name': 'Cranberry Juice', 'category': 'mixers', 'price': Decimal('22.00'), 'description': 'Cranberry juice'},
                
                # Snacks
                {'name': 'Chips & Dip', 'category': 'snacks', 'price': Decimal('35.00'), 'description': 'Crispy chips with cheese dip'},
                {'name': 'Chicken Wings', 'category': 'snacks', 'price': Decimal('65.00'), 'description': 'Spicy chicken wings (6 pieces)'},
                {'name': 'Nachos', 'category': 'snacks', 'price': Decimal('45.00'), 'description': 'Loaded nachos with cheese and jalapeños'},
                {'name': 'Sliders (3)', 'category': 'snacks', 'price': Decimal('85.00'), 'description': 'Three mini burgers'},
                {'name': 'Chicken Strips', 'category': 'snacks', 'price': Decimal('55.00'), 'description': 'Crispy chicken strips with sauce'},
            ]
            
            for prod_data in products_data:
                category = Category.objects.get(slug=prod_data['category'])
                product, created = Product.objects.get_or_create(
                    club=club,
                    name=prod_data['name'],
                    defaults={
                        'category': category,
                        'price': prod_data['price'],
                        'description': prod_data['description'],
                        'is_available': True,
                        'stock_quantity': 100,  # Set high stock for testing
                        'display_order': 0
                    }
                )
                if created:
                    self.stdout.write(f'Created product: {product.name}')
            
            self.stdout.write(
                self.style.SUCCESS('Successfully populated database with sample data!')
            )
            self.stdout.write(f'Club: {club.name}')
            self.stdout.write(f'Tables: {Table.objects.filter(club=club).count()}')
            self.stdout.write(f'Categories: {Category.objects.count()}')
            self.stdout.write(f'Products: {Product.objects.filter(club=club).count()}')
            self.stdout.write('')
            self.stdout.write('Test URLs:')
            self.stdout.write(f'Menu for Table 1: http://localhost:8000/{club.slug}/table/1/')
            self.stdout.write(f'Menu for Table 7: http://localhost:8000/{club.slug}/table/7/')
            self.stdout.write(f'Staff Dashboard: http://localhost:8000/staff/')
            self.stdout.write(f'Admin Dashboard: http://localhost:8000/admin-dashboard/')
