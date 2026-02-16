from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q
from .models import Notification, NotificationPreference, NotificationLog
from .tasks import send_notification
import json

@login_required
def notification_list(request):
    """Get all notifications for the current user."""
    notifications = Notification.objects.filter(user=request.user)
    
    # Apply filters
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    is_read = request.GET.get('is_read')
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        notifications = notifications.filter(is_read=is_read_bool)
    
    priority = request.GET.get('priority')
    if priority:
        notifications = notifications.filter(priority=priority)
    
    # Search
    search = request.GET.get('search')
    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) |
            Q(message__icontains=search)
        )
    
    # Pagination
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    total = notifications.count()
    notifications = notifications[offset:offset + limit]
    
    data = []
    for notification in notifications:
        data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'type_display': notification.get_notification_type_display(),
            'title': notification.title,
            'message': notification.message,
            'priority': notification.priority,
            'priority_display': notification.get_priority_display(),
            'is_read': notification.is_read,
            'is_sent': notification.is_sent,
            'created_at': notification.created_at.isoformat(),
            'time_ago': get_time_ago(notification.created_at),
            'bus': {
                'id': notification.bus.id,
                'number': notification.bus.bus_number,
            } if notification.bus else None,
            'route': {
                'id': notification.route.id,
                'name': notification.route.name,
            } if notification.route else None,
            'trip': {
                'id': notification.trip.id,
            } if notification.trip else None,
        })
    
    return JsonResponse({
        'notifications': data,
        'total': total,
        'limit': limit,
        'offset': offset,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
    })

@login_required
@require_POST
def mark_as_read(request, notification_id=None):
    """Mark notifications as read."""
    if notification_id:
        # Mark single notification as read
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    else:
        # Mark all notifications as read
        count = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return JsonResponse({
            'success': True,
            'message': f'{count} notifications marked as read'
        })

@login_required
@require_POST
def mark_as_unread(request, notification_id):
    """Mark a notification as unread."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = False
    notification.read_at = None
    notification.save(update_fields=['is_read', 'read_at'])
    
    return JsonResponse({
        'success': True,
        'message': 'Notification marked as unread'
    })

@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a notification."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    return JsonResponse({
        'success': True,
        'message': 'Notification deleted'
    })

@login_required
@require_POST
def delete_all_read(request):
    """Delete all read notifications."""
    count = Notification.objects.filter(user=request.user, is_read=True).delete()[0]
    return JsonResponse({
        'success': True,
        'message': f'{count} notifications deleted'
    })

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
                'system': preferences.email_system,
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
                'system': preferences.push_system,
            },
            'quiet_hours': {
                'enabled': preferences.quiet_hours_enabled,
                'start': preferences.quiet_hours_start.strftime('%H:%M') if preferences.quiet_hours_start else None,
                'end': preferences.quiet_hours_end.strftime('%H:%M') if preferences.quiet_hours_end else None,
            },
            'limits': {
                'max_per_hour': preferences.max_notifications_per_hour,
                'max_emails_per_day': preferences.max_emails_per_day,
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
            preferences.email_system = email_prefs.get('system', preferences.email_system)
        
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
            preferences.push_system = push_prefs.get('system', preferences.push_system)
        
        # Update quiet hours
        if 'quiet_hours' in data:
            quiet_hours = data['quiet_hours']
            preferences.quiet_hours_enabled = quiet_hours.get('enabled', preferences.quiet_hours_enabled)
            
            if 'start' in quiet_hours and quiet_hours['start']:
                from datetime import datetime
                preferences.quiet_hours_start = datetime.strptime(quiet_hours['start'], '%H:%M').time()
            if 'end' in quiet_hours and quiet_hours['end']:
                from datetime import datetime
                preferences.quiet_hours_end = datetime.strptime(quiet_hours['end'], '%H:%M').time()
        
        # Update limits
        if 'limits' in data:
            limits = data['limits']
            preferences.max_notifications_per_hour = limits.get('max_per_hour', preferences.max_notifications_per_hour)
            preferences.max_emails_per_day = limits.get('max_emails_per_day', preferences.max_emails_per_day)
        
        preferences.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Preferences updated successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_unread_count(request):
    """Get count of unread notifications."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})

@login_required
def recent_notifications(request):
    """Get recent notifications for dashboard."""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    data = []
    for notification in notifications:
        data.append({
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
    
    return JsonResponse({
        'notifications': data,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count()
    })

def get_time_ago(created_at):
    """Get human-readable time ago string."""
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

@login_required
def notification_stats(request):
    """Get notification statistics."""
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    last_7_days = timezone.now() - timedelta(days=7)
    
    stats = {
        'total': Notification.objects.filter(user=request.user).count(),
        'unread': Notification.objects.filter(user=request.user, is_read=False).count(),
        'read': Notification.objects.filter(user=request.user, is_read=True).count(),
        'by_type': Notification.objects.filter(user=request.user).values('notification_type').annotate(
            count=Count('id')
        ),
        'last_7_days': Notification.objects.filter(
            user=request.user,
            created_at__gte=last_7_days
        ).count(),
    }
    
    return JsonResponse(stats)

@login_required
def subscribe_web_push(request):
    """Subscribe user to web push notifications."""
    # Implementation for web push subscription
    pass

@login_required
def unsubscribe_web_push(request):
    """Unsubscribe user from web push notifications."""
    # Implementation for web push unsubscription
    pass

@login_required
@require_POST
def send_test_notification(request):
    """Send a test notification to the user."""
    notification = Notification.objects.create(
        user=request.user,
        notification_type='system',
        title='Test Notification',
        message='This is a test notification from the system.',
        priority='low',
        send_push=True
    )
    
    # Trigger async sending
    send_notification.delay(notification.id)
    
    return JsonResponse({
        'success': True,
        'message': 'Test notification sent',
        'notification_id': notification.id
    })