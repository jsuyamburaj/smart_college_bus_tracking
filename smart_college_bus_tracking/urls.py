from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from accounts.views import login_view, logout_view, register_view
from accounts import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Public Pages
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),
    path('contact-admin/', views.contact_admin, name='contact_admin'),

    # Authentication
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('accounts/', include('django.contrib.auth.urls')),

    # Dashboard URLs
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),

    # Driver API Endpoints (NEW)
    path('tracking/update-location/<int:bus_id>/', views.update_bus_location, name='update_location'),
    path('api/trips/start/<int:bus_id>/', views.start_trip, name='start_trip'),
    path('api/trips/end/<int:bus_id>/', views.end_trip, name='end_trip'),
    path('api/issues/report/', views.report_issue, name='report_issue'),
    path('driver/passengers/<int:bus_id>/', views.passenger_list, name='passenger_list'),
    path('contact-admin/', views.contact_admin, name='contact_admin'),
    path('my-issues/', views.my_issues, name='my_issues'),

    # App Includes
    path('accounts/', include('accounts.urls')),
    path('buses/', include('buses.urls')),
    path('tracking/', include('tracking.urls')),
    path('api/', include('api.urls')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    # Serve static and media files in DEBUG mode
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug Toolbar URLs
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]