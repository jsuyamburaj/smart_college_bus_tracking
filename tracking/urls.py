from django.urls import path
from . import views

app_name = 'tracking'

urlpatterns = [
    # Student URLs
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('track-bus/', views.track_bus, name='track_bus'),
    path('track-bus/<int:bus_id>/', views.track_bus, name='track_bus_by_id'),
    
    # API URLs
    path('api/update-location/<int:bus_id>/', views.update_location, name='update_location'),
    path('api/bus/<int:bus_id>/history/', views.get_bus_location_history, name='bus_location_history'),
]