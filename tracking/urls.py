from django.urls import path
from . import views
from .views import (update_location,start_trip,stop_trip,get_live_bus_location)
app_name = 'tracking'

urlpatterns = [
    # Student URLs
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('track-bus/', views.track_bus, name='track_bus'),
    path('track-bus/<int:bus_id>/', views.track_bus, name='track_bus_by_id'),
    
    # API URLs
    path('api/update-location/<int:bus_id>/', views.update_location, name='update_location'),
    path('api/bus/<int:bus_id>/history/', views.get_bus_location_history, name='bus_location_history'),

    # update URl
    path('update-location/<int:bus_id>/', update_location, name='update_location'),
    path('start-trip/<int:bus_id>/', start_trip, name='start_trip'),
    path('stop-trip/<int:bus_id>/', stop_trip, name='stop_trip'),
    path('live-location/<int:bus_id>/', get_live_bus_location, name='live_location'),
]
