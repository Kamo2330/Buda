from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('api/order/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('products/', views.product_management, name='product_management'),
    path('api/product/<int:product_id>/toggle/', views.toggle_product_availability, name='toggle_product_availability'),
    path('api/product/<int:product_id>/stock/', views.update_stock, name='update_stock'),
]
