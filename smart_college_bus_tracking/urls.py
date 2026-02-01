from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from accounts.views import login_view, logout_view, register_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('contact/', TemplateView.as_view(template_name='contact.html'), name='contact'),

    # Auth URLs
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),

    # App URLs
    path('accounts/', include('accounts.urls')),
    path('buses/', include('buses.urls')),
    path('tracking/', include('tracking.urls')),
    path('api/', include('api.urls')),
    path('notifications/', include('notifications.urls')),
    path('accounts/', include('django.contrib.auth.urls')),


    # Dashboard
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
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
