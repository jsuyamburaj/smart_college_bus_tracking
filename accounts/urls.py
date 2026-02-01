from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('student/dashboard/', views.dashboard_view, name='student_dashboard'),
    path('password/change/', views.change_password, name='change_password'),
    path('notifications/update/', views.update_notifications, name='update_notifications'),
    path('profile/upload-photo/', views.upload_photo, name='upload_photo'),
    path('student/schedule/', views.student_schedule, name='student_schedule'),
    
    



]
