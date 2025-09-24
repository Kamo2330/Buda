from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('<str:club_slug>/table/<str:table_number>/', views.menu_view, name='menu'),
    path('api/add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('api/update-cart/', views.update_cart, name='update_cart'),
    path('api/remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('<str:club_slug>/table/<str:table_number>/checkout/', views.checkout_view, name='checkout'),
    path('order/<int:order_id>/confirmation/', views.order_confirmation, name='order_confirmation'),
]
