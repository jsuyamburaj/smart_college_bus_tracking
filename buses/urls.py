from django.urls import path
from . import views

app_name = 'buses'

urlpatterns = [
    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/buses/', views.bus_list, name='bus_list'),
    path('admin/buses/<int:bus_id>/', views.bus_detail, name='bus_detail'),
    path('admin/buses/add/', views.add_bus, name='add_bus'),
    path('admin/routes/', views.route_list, name='route_list'),
    
    # Driver URLs
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    
    # API URLs
    path('api/locations/', views.get_bus_locations, name='bus_locations'),
]