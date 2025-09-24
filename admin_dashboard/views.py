from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
import json

from menu.models import Club, Table, Category, Product
from menu.utils import generate_table_qr_code
from orders.models import Order, OrderItem
from .models import SalesReport, ProductSales


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard"""
    # Get basic stats
    total_clubs = Club.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Today's stats
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_revenue = Order.objects.filter(created_at__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Recent orders
    recent_orders = Order.objects.select_related('table', 'club').order_by('-created_at')[:10]
    
    # Top selling products
    top_products = ProductSales.objects.select_related('product').order_by('-revenue')[:5]
    
    context = {
        'total_clubs': total_clubs,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
        'top_products': top_products,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def club_management(request):
    """Manage clubs"""
    clubs = Club.objects.all().order_by('name')
    
    context = {
        'clubs': clubs,
    }
    
    return render(request, 'admin_dashboard/club_management.html', context)


@login_required
@user_passes_test(is_admin)
def club_detail(request, club_id):
    """Detailed view of a specific club"""
    club = get_object_or_404(Club, id=club_id)
    
    # Get club stats
    total_orders = Order.objects.filter(club=club).count()
    total_revenue = Order.objects.filter(club=club).aggregate(total=Sum('total_amount'))['total'] or 0
    total_tables = Table.objects.filter(club=club).count()
    total_products = Product.objects.filter(club=club).count()
    
    # Recent orders for this club
    recent_orders = Order.objects.filter(club=club).select_related('table').order_by('-created_at')[:10]
    
    # Top selling products for this club
    top_products = ProductSales.objects.filter(club=club).select_related('product').order_by('-revenue')[:5]
    
    context = {
        'club': club,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_tables': total_tables,
        'total_products': total_products,
        'recent_orders': recent_orders,
        'top_products': top_products,
    }
    
    return render(request, 'admin_dashboard/club_detail.html', context)


@login_required
@user_passes_test(is_admin)
def menu_management(request, club_id):
    """Manage menu for a specific club"""
    club = get_object_or_404(Club, id=club_id)
    categories = Category.objects.filter(is_active=True).prefetch_related('products__club').filter(products__club=club).distinct()
    products = Product.objects.filter(club=club).select_related('category').order_by('category__display_order', 'display_order')
    
    context = {
        'club': club,
        'categories': categories,
        'products': products,
    }
    
    return render(request, 'admin_dashboard/menu_management.html', context)


@login_required
@user_passes_test(is_admin)
def reports(request):
    """Sales reports and analytics"""
    # Date range for reports (last 30 days by default)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get sales data
    sales_data = Order.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('total_amount')
    ).order_by('day')
    
    # Get product sales data
    product_sales = ProductSales.objects.filter(
        date__range=[start_date, end_date]
    ).select_related('product', 'club').order_by('-revenue')[:20]
    
    # Get hourly distribution
    hourly_data = Order.objects.filter(
        created_at__date__range=[start_date, end_date]
    ).extra(
        select={'hour': 'extract(hour from created_at)'}
    ).values('hour').annotate(
        order_count=Count('id')
    ).order_by('hour')
    
    context = {
        'sales_data': list(sales_data),
        'product_sales': product_sales,
        'hourly_data': list(hourly_data),
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'admin_dashboard/reports.html', context)


@login_required
@user_passes_test(is_admin)
def table_management(request, club_id):
    """Manage tables for a specific club"""
    club = get_object_or_404(Club, id=club_id)
    tables = Table.objects.filter(club=club).order_by('number')
    
    context = {
        'club': club,
        'tables': tables,
    }
    
    return render(request, 'admin_dashboard/table_management.html', context)


@login_required
@user_passes_test(is_admin)
def generate_qr_codes(request, club_id):
    """Generate QR codes for all tables in a club"""
    club = get_object_or_404(Club, id=club_id)
    tables = Table.objects.filter(club=club, is_active=True)
    
    # Generate QR codes for all tables
    qr_codes = []
    for table in tables:
        qr_image = generate_table_qr_code(table)
        qr_codes.append({
            'table': table,
            'qr_image': qr_image,
            'url': f"http://localhost:8000/{club.slug}/table/{table.number}/"
        })
    
    context = {
        'club': club,
        'qr_codes': qr_codes,
        'qr_available': qr_image is not None,
    }
    
    return render(request, 'admin_dashboard/qr_codes.html', context)