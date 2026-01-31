from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification endpoints
    path('', views.notification_list, name='notification_list'),
    path('recent/', views.recent_notifications, name='recent_notifications'),
    path('unread/count/', views.get_unread_count, name='unread_count'),
    path('mark-read/', views.mark_as_read, name='mark_all_read'),
    path('mark-read/<int:notification_id>/', views.mark_as_read, name='mark_read'),
    path('delete/<int:notification_id>/', views.delete_notification, name='delete'),
    
    # Preference endpoints
    path('preferences/', views.get_preferences, name='get_preferences'),
    path('preferences/update/', views.update_preferences, name='update_preferences'),
]