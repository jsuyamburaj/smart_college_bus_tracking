from django.urls import path
from . import views

app_name = 'tracking'

urlpatterns = [
    # ---------------- Student URLs ----------------
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('track-bus/', views.track_bus, name='track_bus'),
    path('track-bus/<int:bus_id>/', views.track_bus, name='track_bus_by_id'),

    # ---------------- API URLs ----------------
    path('api/update-location/<int:bus_id>/', views.update_location, name='api_update_location'),
    path('api/bus/<int:bus_id>/history/', views.get_bus_location_history, name='bus_location_history'),

    # ---------------- Driver URLs ----------------
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('start-trip/<int:bus_id>/', views.start_trip, name='start_trip'),
    path('stop-trip/<int:bus_id>/', views.stop_trip, name='stop_trip'),
    path('live-location/<int:bus_id>/', views.get_live_bus_location, name='live_location'),
]