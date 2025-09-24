from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
import json

from orders.models import Order, OrderItem
from menu.models import Club, Product


@login_required
def dashboard(request):
    """Staff dashboard showing all orders"""
    # Get all active orders for the staff member's club
    # For now, we'll show all orders - in production, filter by staff member's club
    orders = Order.objects.filter(
        status__in=['received', 'in_progress', 'ready']
    ).select_related('table', 'club').prefetch_related('items__product').order_by('-created_at')
    
    # Group orders by status
    received_orders = orders.filter(status='received')
    in_progress_orders = orders.filter(status='in_progress')
    ready_orders = orders.filter(status='ready')
    
    context = {
        'received_orders': received_orders,
        'in_progress_orders': in_progress_orders,
        'ready_orders': ready_orders,
    }
    
    return render(request, 'staff/dashboard.html', context)


@login_required
def order_detail(request, order_id):
    """Detailed view of a specific order"""
    order = get_object_or_404(Order, id=order_id)
    
    context = {
        'order': order,
    }
    
    return render(request, 'staff/order_detail.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'})
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        valid_statuses = ['received', 'in_progress', 'ready', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
        
        order = get_object_or_404(Order, id=order_id)
        order.status = new_status
        
        if new_status == 'delivered':
            from django.utils import timezone
            order.delivered_at = timezone.now()
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order status updated to {order.get_status_display()}'
        })
        
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'message': 'Invalid data'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})


@login_required
def product_management(request):
    """Manage product availability and stock"""
    # Get all products for the staff member's club
    # For now, show all products - in production, filter by staff member's club
    products = Product.objects.filter(is_available=True).select_related('club', 'category').order_by('category__display_order', 'display_order')
    
    context = {
        'products': products,
    }
    
    return render(request, 'staff/product_management.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_product_availability(request, product_id):
    """Toggle product availability via AJAX"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'})
    
    try:
        product = get_object_or_404(Product, id=product_id)
        product.is_available = not product.is_available
        product.save()
        
        status = 'available' if product.is_available else 'unavailable'
        return JsonResponse({
            'success': True,
            'message': f'{product.name} is now {status}',
            'is_available': product.is_available
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found'})


@csrf_exempt
@require_http_methods(["POST"])
def update_stock(request, product_id):
    """Update product stock via AJAX"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'})
    
    try:
        data = json.loads(request.body)
        stock_quantity = int(data.get('stock_quantity', 0))
        
        product = get_object_or_404(Product, id=product_id)
        product.stock_quantity = stock_quantity
        product.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Stock updated for {product.name}',
            'stock_quantity': product.stock_quantity
        })
        
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'message': 'Invalid data'})
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found'})