from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import IssueViewSet


router = DefaultRouter()

# Register ViewSets
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'students', views.StudentProfileViewSet, basename='student')
router.register(r'drivers', views.DriverProfileViewSet, basename='driver')
router.register(r'parents', views.ParentProfileViewSet, basename='parent')
router.register(r'buses', views.BusViewSet, basename='bus')
router.register(r'routes', views.RouteViewSet, basename='route')
router.register(r'schedules', views.ScheduleViewSet, basename='schedule')
router.register(r'trips', views.TripViewSet, basename='trip')
router.register(r'locations', views.LocationHistoryViewSet, basename='location')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'issues', views.IssueViewSet, basename='issue')
urlpatterns = [
    # Auth endpoints
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/logout/', views.LogoutView.as_view(), name='api_logout'),
    path('auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('auth/me/', views.CurrentUserView.as_view(), name='api_current_user'),
    path('auth/password-reset/', views.password_reset, name='api_password_reset'),
    path('auth/password-reset/confirm/', views.password_reset_confirm, name='api_password_reset_confirm'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='api_dashboard'),
    
    # Analytics
    path('analytics/', views.AnalyticsView.as_view(), name='api_analytics'),
    
    # Public endpoints
    path('public/stats/', views.public_stats, name='api_public_stats'),
    path('public/bus-locations/', views.BusViewSet.as_view({'get': 'public_locations'}), name='api_public_bus_locations'),
    path('public/search/buses/', views.search_buses, name='api_search_buses'),
    path('public/search/stops/', views.search_stops, name='api_search_stops'),
    
    # Include router URLs
    path('', include(router.urls)),
]