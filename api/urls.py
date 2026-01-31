from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Register ViewSets
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'students', views.StudentProfileViewSet, basename='student')
router.register(r'drivers', views.DriverProfileViewSet, basename='driver')
router.register(r'buses', views.BusViewSet, basename='bus')
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'stops', views.StopViewSet, basename='stop')
router.register(r'schedules', views.ScheduleViewSet, basename='schedule')
router.register(r'locations', views.LocationHistoryViewSet, basename='location')
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardAPI.as_view(), name='api_dashboard'),
    
    # Public APIs
    path('public/bus-locations/', views.BusLocationsAPI.as_view(), name='public_bus_locations'),
    path('public/route/<int:route_id>/stops/', views.RouteStopsAPI.as_view(), name='public_route_stops'),
    
    # Include router URLs
    path('', include(router.urls)),
]