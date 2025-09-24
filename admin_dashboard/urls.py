from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('clubs/', views.club_management, name='club_management'),
    path('clubs/<int:club_id>/', views.club_detail, name='club_detail'),
    path('clubs/<int:club_id>/menu/', views.menu_management, name='menu_management'),
    path('clubs/<int:club_id>/tables/', views.table_management, name='table_management'),
    path('clubs/<int:club_id>/qr-codes/', views.generate_qr_codes, name='qr_codes'),
    path('reports/', views.reports, name='reports'),
]
