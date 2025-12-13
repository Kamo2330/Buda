# Hamba - Flight Booking Management System

A Django-based flight booking platform for managing flight searches, bookings, travelers, and payments with support for add-ons and extras.

## 📋 Overview

Hamba is a modern travel booking platform that enables users to:
- Search for available flights
- Book flights with multiple travelers
- Add booking extras (insurance, date change options, ticket delivery methods)
- Process payments
- Manage booking confirmations

**Project Type:** Django Web Application  
**Python Version:** 3.10+  
**Django Version:** 5.2  
**Database:** SQLite (development), configurable for production  

---

## 🏗️ Project Structure

```
Hamba/
├── booking/                          # Main booking app
│   ├── models.py                    # Database models
│   ├── views.py                     # View logic
│   ├── forms.py                     # Django forms
│   ├── urls.py                      # URL routing
│   ├── admin.py                     # Django admin configuration
│   ├── templates/booking/           # HTML templates
│   │   ├── base.html               # Base template
│   │   ├── home.html               # Flight search home
│   │   ├── search_results.html      # Flight results
│   │   ├── booking_summary.html     # Booking review
│   │   ├── traveler_details.html    # Traveler information
│   │   ├── payer_details.html       # Payment details
│   │   ├── payment_method.html      # Payment method selection
│   │   └── confirmation.html        # Booking confirmation
│   └── static/booking/              # Static assets
│       ├── css/style.css            # Styling
│       └── js/main.js               # JavaScript functionality
├── Hamba/                           # Project configuration
│   ├── settings.py                  # Django settings
│   ├── urls.py                      # Main URL configuration
│   ├── wsgi.py                      # WSGI application
│   └── asgi.py                      # ASGI application
├── manage.py                        # Django management script
├── db.sqlite3                       # SQLite database (development)
└── staticfiles/                     # Collected static files
```

---

## 🗄️ Database Models

### **Booking**
- `reference`: Unique booking identifier (HAM12345)
- `status`: PENDING, CONFIRMED, CANCELLED, FAILED
- `total_base_fare`, `total_taxes`, `total_extras`, `total_price`: Pricing breakdown
- `currency`: Currency code (ZAR, USD, etc.)
- `contact_email`, `contact_phone`: Primary contact information
- `source`: Booking source (web, agent, etc.)
- `created_at`, `updated_at`: Timestamps
- `internal_notes`: Admin notes

### **Traveler**
- `booking`: Foreign key to Booking
- `first_name`, `last_name`: Traveler name
- `date_of_birth`: Birth date
- `document_number`: ID/Passport number
- `nationality`: Nationality
- `is_primary_contact`: Primary contact flag
- `special_requests`: Special requests text

### **Payer**
- `booking`: One-to-one relationship with Booking
- `first_name`, `last_name`: Payer name
- `email`, `phone`: Contact information
- `billing_address_*`: Full billing address fields

### **FlightSegment**
- `booking`: Foreign key to Booking
- `airline_name`, `flight_number`: Flight identification
- `origin/destination_airport_code/name`: Route information
- `departure_datetime`, `arrival_datetime`: Timing
- `cabin_class`: Economy, Business, etc.
- `hand_baggage_kg`, `checked_baggage_kg`: Baggage allowances
- `direction`: OUTBOUND or RETURN

### **BookingExtra**
- `booking`: Foreign key to Booking
- `extra_type`: WHATSAPP_TICKET, SMS_TICKET, REFUND_INSURANCE, DATE_CHANGE_OPTION
- `price`, `currency`: Extra cost
- `applies_to_all_travelers`: Boolean flag
- `applies_to_travelers`: M2M relationship for selective application

### **Payment**
- `booking`: One-to-one relationship with Booking
- `method`: CARD, EFT, WALLET
- Payment processing and tracking fields

---

## 🔄 User Flow / Workflow

```
1. Home Page (Flight Search)
   └─> User searches for flights (origin, destination, dates, passengers)

2. Search Results
   └─> System displays mock flight options
   └─> User selects a flight

3. Booking Summary
   └─> Review selected flight and pricing
   └─> Confirm to proceed

4. Traveler Details
   └─> Enter information for each traveler
   └─> Add special requests

5. Payer Details
   └─> Enter billing information
   └─> Add contact details

6. Payment Method
   └─> Select payment method (Card, EFT, Mobile Wallet)
   └─> Add optional extras (insurance, date change, ticket delivery)

7. Process Payment
   └─> Process payment transaction

8. Confirmation
   └─> Display booking confirmation with reference
   └─> Send confirmation email
```

---

## 📦 Available Booking Extras

| Extra Type | Description | Use Case |
|-----------|-----------|----------|
| WHATSAPP_TICKET | Get ticket via WhatsApp | Quick digital delivery |
| SMS_TICKET | Get ticket via SMS | Simple notification |
| REFUND_INSURANCE | Full refund insurance | Protection against illness/death/hospitalization |
| DATE_CHANGE_OPTION | One date change without airline penalty | Booking flexibility |

---

## 🔌 Views & URL Routes

| Route | View | Purpose |
|-------|------|---------|
| `/` | `home()` | Flight search form |
| `/search/` | `search_results()` | Display mock flight results |
| `/booking/summary/` | `booking_summary()` | Review booking details |
| `/booking/travelers/` | `traveler_details()` | Collect traveler information |
| `/booking/payer/` | `payer_details()` | Collect payer billing info |
| `/booking/payment/` | `payment_method()` | Select payment method |
| `/booking/process/` | `process_payment()` | Process payment |
| `/booking/confirmation/<ref>/` | `confirmation()` | Display confirmation |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- pip or conda
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Hamba
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install django==5.2
   # Add any additional requirements to requirements.txt
   ```

4. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser** (for admin access)
   ```bash
   python manage.py createsuperuser
   ```

6. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

   Access the application at `http://localhost:8000`

---

## 👨‍💼 Admin Interface

Access Django admin at `/admin/`:
- Manage bookings with inline travelers, extras, and flight segments
- View and edit payer information
- Track payment records
- Filter by status, currency, and dates

---

## 🔐 Security Considerations

> ⚠️ **CRITICAL**: The following security issues must be addressed before production:

1. **DEBUG mode is enabled** - Set `DEBUG = False` in production
2. **Secret key is exposed** - Generate a new secret key and use environment variables
3. **No ALLOWED_HOSTS configured** - Add your domain(s)
4. **No HTTPS enforcement** - Enable SECURE_SSL_REDIRECT in production
5. **Database is SQLite** - Use PostgreSQL or MySQL for production
6. **No authentication/permissions** - Implement proper access control
7. **No API rate limiting** - Add rate limiting for payment endpoints

---

## 📝 Configuration

### Django Settings (`Hamba/settings.py`)

**Key Settings:**
- `INSTALLED_APPS`: Django admin, auth, sessions, messages, staticfiles, booking app
- `DATABASES`: SQLite (configurable)
- `TEMPLATES`: Django template engine with app directories
- `STATIC_URL`: `/static/` (collected in `staticfiles/`)

**To override settings:**
```python
# Create a .env file and use python-dotenv
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv)
```

---

## 🧪 Testing

Currently, no test suite is configured. Add tests using Django's testing framework:

```python
# booking/tests.py
from django.test import TestCase
from .models import Booking

class BookingTestCase(TestCase):
    def test_booking_reference_generation(self):
        # Test booking reference generation
        pass
```

Run tests:
```bash
python manage.py test
```

---

## 📚 Forms

**Available Forms:**
- `FlightSearchForm`: Trip type, origin, destination, dates, passengers
- `TravelerForm`: Traveler personal and travel document information
- `PayerForm`: Payer name, email, billing address
- `ExtrasForm`: Selection and configuration of booking extras
- `PaymentMethodForm`: Payment method selection

---

## 🎨 Frontend

**Templates:**
- Responsive HTML5 templates
- Bootstrap-compatible CSS framework
- JavaScript for form validation and interactivity

**Static Files:**
- `style.css`: Main styling
- `main.js`: Client-side functionality

---

## 🔧 Common Commands

```bash
# Run development server
python manage.py runserver

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access Django shell
python manage.py shell

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test

# Export data
python manage.py dumpdata > data.json

# Import data
python manage.py loaddata data.json
```

---

## 📄 Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DATABASE_URL=sqlite:///db.sqlite3
# Or for PostgreSQL: postgresql://user:password@localhost:5432/hamba

# Email (for confirmations)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Payment Gateway (if applicable)
PAYMENT_GATEWAY_API_KEY=your-api-key
```

---

## 🚢 Deployment

### Using Gunicorn + Nginx

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn Hamba.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "Hamba.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Environment Setup for Production
1. Set `DEBUG = False`
2. Configure proper `ALLOWED_HOSTS`
3. Set strong `SECRET_KEY`
4. Enable `SECURE_SSL_REDIRECT`
5. Configure CSRF and security headers
6. Use PostgreSQL or MySQL
7. Configure proper email backend for confirmations
8. Set up static files serving
9. Configure database backups
10. Set up monitoring and logging

---

## 📞 Support & Contact

For issues or questions, please contact the development team.

---

## 📄 License

[Add your license information here]

---

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Write tests
4. Submit a pull request

---

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Security](https://docs.djangoproject.com/en/5.2/topics/security/)

---

**Last Updated:** December 2025  
**Version:** 1.0.0-alpha
