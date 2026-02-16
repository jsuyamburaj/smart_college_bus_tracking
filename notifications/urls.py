from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification endpoints
    path('', views.notification_list, name='list'),
    path('recent/', views.recent_notifications, name='recent'),
    path('unread/count/', views.get_unread_count, name='unread_count'),
    path('stats/', views.notification_stats, name='stats'),
    
    # Mark as read/unread
    path('mark-read/', views.mark_as_read, name='mark_all_read'),
    path('mark-read/<int:notification_id>/', views.mark_as_read, name='mark_read'),
    path('mark-unread/<int:notification_id>/', views.mark_as_unread, name='mark_unread'),
    
    # Delete
    path('delete/<int:notification_id>/', views.delete_notification, name='delete'),
    path('delete-all-read/', views.delete_all_read, name='delete_all_read'),
    
    # Preferences
    path('preferences/', views.get_preferences, name='get_preferences'),
    path('preferences/update/', views.update_preferences, name='update_preferences'),
    
    # Test
    path('test/', views.send_test_notification, name='test'),
    
    # Web Push (to be implemented)
    path('subscribe/', views.subscribe_web_push, name='subscribe'),
    path('unsubscribe/', views.unsubscribe_web_push, name='unsubscribe'),
]