from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Q
import json

from .models import Club, Table, Category, Product
from orders.models import Order, OrderItem


def home_view(request):
    """Home page with club selection"""
    clubs = Club.objects.filter(is_active=True)
    
    context = {
        'clubs': clubs,
    }
    
    return render(request, 'menu/home.html', context)


def menu_view(request, club_slug, table_number):
    """Main menu page for customers"""
    club = get_object_or_404(Club, slug=club_slug, is_active=True)
    table = get_object_or_404(Table, club=club, number=table_number, is_active=True)
    
    # Get all active categories with their products
    categories = Category.objects.filter(is_active=True).prefetch_related(
        'products__club'
    ).filter(products__club=club, products__is_available=True).distinct()
    
    # Get cart from session
    cart = request.session.get('cart', {})
    cart_items = []
    cart_total = 0
    
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id, club=club, is_available=True)
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            cart_total += item_total
        except Product.DoesNotExist:
            # Remove invalid items from cart
            del cart[product_id]
    
    request.session['cart'] = cart
    
    context = {
        'club': club,
        'table': table,
        'categories': categories,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': sum(cart.values()) if cart else 0,
    }
    
    return render(request, 'menu/menu.html', context)


def add_to_cart(request):
    """Add item to cart via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            
            product = get_object_or_404(Product, id=product_id, is_available=True)
            
            # Get or create cart in session
            cart = request.session.get('cart', {})
            current_quantity = cart.get(str(product_id), 0)
            cart[str(product_id)] = current_quantity + quantity
            
            request.session['cart'] = cart
            
            return JsonResponse({
                'success': True,
                'cart_count': sum(cart.values()),
                'message': f'{product.name} added to cart'
            })
            
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'message': 'Invalid data'})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def update_cart(request):
    """Update cart item quantity via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 0))
            
            cart = request.session.get('cart', {})
            
            if quantity <= 0:
                cart.pop(str(product_id), None)
            else:
                cart[str(product_id)] = quantity
            
            request.session['cart'] = cart
            
            return JsonResponse({
                'success': True,
                'cart_count': sum(cart.values()),
            })
            
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def remove_from_cart(request):
    """Remove item from cart via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            cart = request.session.get('cart', {})
            cart.pop(str(product_id), None)
            request.session['cart'] = cart
            
            return JsonResponse({
                'success': True,
                'cart_count': sum(cart.values()),
            })
            
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({'success': False, 'message': 'Invalid data'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def checkout_view(request, club_slug, table_number):
    """Checkout page"""
    club = get_object_or_404(Club, slug=club_slug, is_active=True)
    table = get_object_or_404(Table, club=club, number=table_number, is_active=True)
    
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, 'Your cart is empty!')
        return redirect('menu', club_slug=club_slug, table_number=table_number)
    
    # Build cart items with product details
    cart_items = []
    cart_total = 0
    
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id, club=club, is_available=True)
            item_total = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total
            })
            cart_total += item_total
        except Product.DoesNotExist:
            # Remove invalid items from cart
            del cart[product_id]
    
    request.session['cart'] = cart
    
    if request.method == 'POST':
        # Create order
        order = Order.objects.create(
            club=club,
            table=table,
            payment_method=request.POST.get('payment_method', 'pay_at_table')
        )
        
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                unit_price=item['product'].price
            )
        
        # Clear cart
        request.session['cart'] = {}
        
        messages.success(request, f'Order #{order.order_number} placed successfully!')
        return redirect('order_confirmation', order_id=order.id)
    
    context = {
        'club': club,
        'table': table,
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    
    return render(request, 'menu/checkout.html', context)


def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)
    
    context = {
        'order': order,
    }
    
    return render(request, 'menu/order_confirmation.html', context)