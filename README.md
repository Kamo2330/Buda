# Buda - Club/Bar Ordering System 🍺

A modern, mobile-friendly ordering system for clubs and bars that eliminates queues and speeds up service through QR code-based ordering.

## 🎯 Features

### Customer Experience
- **QR Code Ordering**: Customers scan QR codes at their table to access the menu
- **Mobile-First Design**: Optimized for one-handed mobile use with thumb-friendly interface
- **Real-Time Cart**: Add items to cart with instant updates
- **Multiple Payment Options**: Pay at table or online
- **Order Tracking**: Real-time order status updates

### Staff Management
- **Live Order Dashboard**: View incoming orders by table
- **Order Status Management**: Track orders from received → in progress → ready → delivered
- **Product Management**: Mark items as sold out, update stock levels
- **Table Management**: Manage table assignments and QR codes

### Admin Dashboard
- **Club Management**: Manage multiple venues
- **Menu Management**: Upload products, set prices, manage categories
- **Sales Analytics**: Track sales, popular items, peak hours
- **QR Code Generation**: Generate printable QR codes for tables
- **Staff Management**: Manage staff accounts and permissions

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Django 5.2+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Buda
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Create sample data**
   ```bash
   python manage.py populate_sample_data
   ```

5. **Create admin user**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

### Access the System

- **Customer Menu**: `http://localhost:8000/test-club/table/1/`
- **Staff Dashboard**: `http://localhost:8000/staff/` (login required)
- **Admin Dashboard**: `http://localhost:8000/admin-dashboard/` (admin required)
- **Django Admin**: `http://localhost:8000/admin/` (admin required)

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

## 📱 How It Works

### Customer Flow
1. Customer sits at Table 7
2. Scans QR code on table
3. Sees menu with "Order fast, chill more 🍺"
4. Browses categories: Beers, Ciders, Spirits, Mixers, Snacks
5. Adds items to cart
6. Proceeds to checkout
7. Chooses payment method (pay at table or online)
8. Places order
9. Waiter receives order notification
10. Waiter delivers to Table 7

### Staff Flow
1. Staff logs into dashboard
2. Sees new orders in "Received" tab
3. Clicks "Start Preparing" → order moves to "In Progress"
4. When ready, clicks "Mark Ready" → order moves to "Ready"
5. After delivery, clicks "Mark Delivered" → order completed

### Admin Flow
1. Admin creates club and tables
2. Adds products to menu with prices and images
3. Generates QR codes for each table
4. Prints and places QR codes on tables
5. Monitors sales and analytics

## 🎨 Design Features

- **Black & Neon Theme**: Club atmosphere with neon green, blue, and pink accents
- **Mobile Optimized**: Thumb-friendly buttons and one-handed navigation
- **Responsive Design**: Works on phones, tablets, and desktops
- **Fast Loading**: Optimized for quick menu browsing
- **Intuitive UX**: Clear visual hierarchy and easy navigation

## 🛠 Technical Stack

- **Backend**: Django 5.2
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **QR Codes**: qrcode library
- **Images**: Pillow for image processing

## 📊 Database Models

### Core Models
- **Club**: Venue information (name, address, contact)
- **Table**: Table/booth with unique QR code
- **Category**: Product categories (Beers, Ciders, etc.)
- **Product**: Individual items with pricing and availability
- **Order**: Customer orders with status tracking
- **OrderItem**: Individual items within an order

### Admin Models
- **StaffMember**: Staff accounts and permissions
- **SalesReport**: Daily sales analytics
- **ProductSales**: Product-specific sales data

## 🔧 Configuration

### Environment Variables
Create a `.env` file for production:
```env
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:pass@localhost/buda
```

### Settings
Key settings in `Buda/settings.py`:
- `TIME_ZONE = 'Africa/Johannesburg'` (South African timezone)
- `MEDIA_ROOT` and `MEDIA_URL` for file uploads
- `STATIC_ROOT` and `STATIC_URL` for static files

## 🚀 Deployment

### Production Checklist
1. Set `DEBUG = False`
2. Configure `ALLOWED_HOSTS`
3. Set up PostgreSQL database
4. Configure static file serving
5. Set up media file serving
6. Configure email settings
7. Set up SSL certificate
8. Configure domain and DNS

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "Buda.wsgi:application"]
```

## 📈 Future Features

- **Real-time Updates**: WebSocket integration for live order updates
- **Payment Integration**: Stripe, PayPal, SnapScan integration
- **Loyalty Program**: Points system for frequent customers
- **Split Bills**: Multiple payment methods per order
- **Push Notifications**: Order status updates
- **Inventory Management**: Stock tracking and low stock alerts
- **Analytics Dashboard**: Advanced reporting and insights
- **Multi-language Support**: Multiple language options
- **POS Integration**: Connect with existing point-of-sale systems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Email: support@buda.co.za
- Documentation: [Link to docs]

## 🎉 Acknowledgments

- Django community for the excellent framework
- Bootstrap team for the responsive UI components
- South African bar/club owners for the inspiration

---

**Buda** - Order fast, chill more! 🍺
"# Buda" 
