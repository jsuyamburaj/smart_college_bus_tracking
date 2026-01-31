from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q
from .models import Notification, NotificationPreference
import json

@login_required
def notification_list(request):
    """Get all notifications for the current user."""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark as read if requested
    mark_read = request.GET.get('mark_read', False)
    if mark_read:
        notifications.update(is_read=True)
    
    # Filter by type if specified
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # Filter by read status
    is_read = request.GET.get('is_read')
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        notifications = notifications.filter(is_read=is_read_bool)
    
    # Limit results
    limit = request.GET.get('limit', 50)
    notifications = notifications[:int(limit)]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'type_display': notification.get_notification_type_display(),
            'title': notification.title,
            'message': notification.message,
            'priority': notification.priority,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'bus': {
                'id': notification.bus.id,
                'number': notification.bus.bus_number,
            } if notification.bus else None,
            'route': {
                'id': notification.route.id,
                'name': notification.route.name,
            } if notification.route else None,
        })
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
        'total_count': Notification.objects.filter(user=request.user).count(),
    })

@login_required
@require_POST
def mark_as_read(request, notification_id=None):
    """Mark notifications as read."""
    if notification_id:
        # Mark single notification as read
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True, 'message': 'Notification marked as read'})
    else:
        # Mark all notifications as read
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True, 'message': 'All notifications marked as read'})

@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a notification."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    return JsonResponse({'success': True, 'message': 'Notification deleted'})

@login_required
def get_preferences(request):
    """Get user's notification preferences."""
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    return JsonResponse({
        'preferences': {
            'email': {
                'bus_arrival': preferences.email_bus_arrival,
                'bus_delay': preferences.email_bus_delay,
                'emergency': preferences.email_emergency,
                'route_change': preferences.email_route_change,
                'maintenance': preferences.email_maintenance,
                'announcements': preferences.email_announcements,
            },
            'sms': {
                'bus_arrival': preferences.sms_bus_arrival,
                'bus_delay': preferences.sms_bus_delay,
                'emergency': preferences.sms_emergency,
                'route_change': preferences.sms_route_change,
            },
            'push': {
                'bus_arrival': preferences.push_bus_arrival,
                'bus_delay': preferences.push_bus_delay,
                'emergency': preferences.push_emergency,
                'route_change': preferences.push_route_change,
                'maintenance': preferences.push_maintenance,
                'announcements': preferences.push_announcements,
            },
            'quiet_hours': {
                'enabled': preferences.respect_quiet_hours,
                'start': preferences.quiet_hours_start.strftime('%H:%M') if preferences.quiet_hours_start else None,
                'end': preferences.quiet_hours_end.strftime('%H:%M') if preferences.quiet_hours_end else None,
            }
        }
    })

@login_required
@require_POST
def update_preferences(request):
    """Update user's notification preferences."""
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    try:
        data = json.loads(request.body)
        
        # Update email preferences
        if 'email' in data:
            email_prefs = data['email']
            preferences.email_bus_arrival = email_prefs.get('bus_arrival', preferences.email_bus_arrival)
            preferences.email_bus_delay = email_prefs.get('bus_delay', preferences.email_bus_delay)
            preferences.email_emergency = email_prefs.get('emergency', preferences.email_emergency)
            preferences.email_route_change = email_prefs.get('route_change', preferences.email_route_change)
            preferences.email_maintenance = email_prefs.get('maintenance', preferences.email_maintenance)
            preferences.email_announcements = email_prefs.get('announcements', preferences.email_announcements)
        
        # Update SMS preferences
        if 'sms' in data:
            sms_prefs = data['sms']
            preferences.sms_bus_arrival = sms_prefs.get('bus_arrival', preferences.sms_bus_arrival)
            preferences.sms_bus_delay = sms_prefs.get('bus_delay', preferences.sms_bus_delay)
            preferences.sms_emergency = sms_prefs.get('emergency', preferences.sms_emergency)
            preferences.sms_route_change = sms_prefs.get('route_change', preferences.sms_route_change)
        
        # Update push preferences
        if 'push' in data:
            push_prefs = data['push']
            preferences.push_bus_arrival = push_prefs.get('bus_arrival', preferences.push_bus_arrival)
            preferences.push_bus_delay = push_prefs.get('bus_delay', preferences.push_bus_delay)
            preferences.push_emergency = push_prefs.get('emergency', preferences.push_emergency)
            preferences.push_route_change = push_prefs.get('route_change', preferences.push_route_change)
            preferences.push_maintenance = push_prefs.get('maintenance', preferences.push_maintenance)
            preferences.push_announcements = push_prefs.get('announcements', preferences.push_announcements)
        
        # Update quiet hours
        if 'quiet_hours' in data:
            quiet_hours = data['quiet_hours']
            preferences.respect_quiet_hours = quiet_hours.get('enabled', preferences.respect_quiet_hours)
            
            if 'start' in quiet_hours:
                preferences.quiet_hours_start = quiet_hours['start']
            if 'end' in quiet_hours:
                preferences.quiet_hours_end = quiet_hours['end']
        
        preferences.save()
        
        return JsonResponse({'success': True, 'message': 'Preferences updated successfully'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def get_unread_count(request):
    """Get count of unread notifications."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})

@login_required
def recent_notifications(request):
    """Get recent notifications (for dashboard)."""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'type_display': notification.get_notification_type_display(),
            'title': notification.title,
            'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
            'priority': notification.priority,
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': get_time_ago(notification.created_at),
        })
    
    return JsonResponse({'notifications': notifications_data})

def get_time_ago(created_at):
    """Helper function to get human-readable time ago."""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    diff = now - created_at
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"