from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search_results, name='search_results'),
    path('booking/summary/', views.booking_summary, name='booking_summary'),
    path('booking/travelers/', views.traveler_details, name='traveler_details'),
    path('booking/payer/', views.payer_details, name='payer_details'),
    path('booking/payment/', views.payment_method, name='payment_method'),
    path('booking/process/', views.process_payment, name='process_payment'),
    path('booking/confirmation/<str:booking_ref>/', views.confirmation, name='confirmation'),
]




