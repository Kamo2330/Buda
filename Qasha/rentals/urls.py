from django.urls import path
from . import views

app_name = 'rentals'

urlpatterns = [
    path('', views.PropertyListView.as_view(), name='property_list'),
    path('messages/', views.message_inbox, name='message_inbox'),
    path('messages/with/<int:other_user_id>/', views.message_thread, name='message_thread'),

    path('manage/', views.my_hub, name='my_hub'),
    path('manage/promotions/', views.promotions_hub, name='promotions'),
    path('property/<int:pk>/promote/', views.promote_listing, name='promote_listing'),
    path('account/', views.my_hub),  # legacy URL
    path('my-qasha/', views.my_hub),  # legacy URL
    path('saved/', views.wishlist_view, name='wishlist'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('rental-requests/', views.host_applications, name='host_applications'),

    path('property/<int:pk>/', views.PropertyDetailView.as_view(), name='property_detail'),

    path('list-property/', views.PropertyCreateView.as_view(), name='property_create'),
    path('my-listings/', views.my_listings, name='my_listings'),
    path('property/<int:pk>/edit/', views.PropertyUpdateView.as_view(), name='property_update'),
    path('property/<int:pk>/delete/', views.property_delete, name='property_delete'),
    path('property/<int:pk>/toggle-available/', views.property_toggle_available, name='property_toggle_available'),
    path('property/<int:pk>/toggle-occupied/', views.property_toggle_occupied, name='property_toggle_occupied'),
    path('property/<int:property_id>/image/<int:image_id>/set-primary/', views.set_primary_image, name='set_primary_image'),

    path('property/<int:property_id>/add-to-wishlist/', views.add_to_wishlist, name='add_to_wishlist'),
    path('property/<int:property_id>/remove-from-wishlist/', views.remove_from_wishlist, name='remove_from_wishlist'),

    path('property/<int:property_id>/book/', views.create_booking, name='create_booking'),
    path('bookings/<int:booking_id>/accept/', views.booking_accept, name='booking_accept'),
    path('bookings/<int:booking_id>/decline/', views.booking_decline, name='booking_decline'),
    path('bookings/<int:booking_id>/pay/', views.booking_pay, name='booking_pay'),
    path('bookings/<int:booking_id>/cancel/', views.booking_cancel, name='booking_cancel'),

    path('property/<int:property_id>/message/', views.send_message, name='send_message'),
    path('property/<int:property_id>/feedback/', views.add_review, name='add_review'),
    path('manage/feedback/', views.host_feedback, name='host_feedback'),
]
