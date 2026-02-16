from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_notification(notification_id):
    """Send a notification asynchronously."""
    from .models import Notification, NotificationLog, NotificationPreference
    
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Check if notification is already sent
        if notification.is_sent:
            logger.info(f"Notification {notification_id} already sent")
            return
        
        # Get user preferences
        try:
            preferences = NotificationPreference.objects.get(user=notification.user)
        except NotificationPreference.DoesNotExist:
            preferences = None
        
        # Check quiet hours
        if preferences and preferences.quiet_hours_enabled:
            current_time = timezone.now().time()
            if preferences.quiet_hours_start and preferences.quiet_hours_end:
                if preferences.quiet_hours_start <= preferences.quiet_hours_end:
                    if preferences.quiet_hours_start <= current_time <= preferences.quiet_hours_end:
                        logger.info(f"Skipping notification during quiet hours for user {notification.user.id}")
                        return
                else:
                    if current_time >= preferences.quiet_hours_start or current_time <= preferences.quiet_hours_end:
                        logger.info(f"Skipping notification during quiet hours for user {notification.user.id}")
                        return
        
        # Send push notification
        if notification.send_push:
            if not preferences or preferences.should_send(notification.notification_type, 'push'):
                send_push_notification.delay(notification_id)
        
        # Send email
        if notification.send_email:
            if not preferences or preferences.should_send(notification.notification_type, 'email'):
                send_email_notification.delay(notification_id)
        
        # Send SMS
        if notification.send_sms:
            if not preferences or preferences.should_send(notification.notification_type, 'sms'):
                send_sms_notification.delay(notification_id)
        
        notification.mark_as_sent()
        
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as e:
        logger.error(f"Error sending notification {notification_id}: {str(e)}")

@shared_task
def send_push_notification(notification_id):
    """Send push notification."""
    from .models import Notification, NotificationLog
    
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Create log entry
        log = NotificationLog.objects.create(
            notification=notification,
            delivery_method='push',
            status='pending'
        )
        
        # TODO: Implement actual push notification sending
        # This would integrate with Firebase Cloud Messaging, Web Push, etc.
        
        # For now, just mark as sent
        log.mark_sent()
        
        logger.info(f"Push notification sent for notification {notification_id}")
        
    except Exception as e:
        logger.error(f"Error sending push notification {notification_id}: {str(e)}")

@shared_task
def send_email_notification(notification_id):
    """Send email notification."""
    from .models import Notification, NotificationLog
    
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Create log entry
        log = NotificationLog.objects.create(
            notification=notification,
            delivery_method='email',
            status='pending'
        )
        
        # Send email
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            fail_silently=True,
        )
        
        log.mark_sent()
        logger.info(f"Email sent for notification {notification_id} to {notification.user.email}")
        
    except Exception as e:
        logger.error(f"Error sending email notification {notification_id}: {str(e)}")

@shared_task
def send_sms_notification(notification_id):
    """Send SMS notification."""
    from .models import Notification, NotificationLog
    
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Create log entry
        log = NotificationLog.objects.create(
            notification=notification,
            delivery_method='sms',
            status='pending'
        )
        
        # TODO: Implement SMS sending (Twilio, etc.)
        
        log.mark_sent()
        logger.info(f"SMS sent for notification {notification_id}")
        
    except Exception as e:
        logger.error(f"Error sending SMS notification {notification_id}: {str(e)}")

@shared_task
def process_scheduled_notifications():
    """Process notifications scheduled for sending."""
    from .models import Notification
    
    now = timezone.now()
    scheduled = Notification.objects.filter(
        scheduled_for__lte=now,
        is_sent=False
    )
    
    for notification in scheduled:
        send_notification.delay(notification.id)
    
    logger.info(f"Processed {scheduled.count()} scheduled notifications")

@shared_task
def cleanup_old_notifications():
    """Delete old notifications."""
    from .models import Notification
    
    # Delete notifications older than 30 days
    cutoff = timezone.now() - timedelta(days=30)
    count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
    
    logger.info(f"Deleted {count} old notifications")

@shared_task
def send_batch_notifications(notification_ids):
    """Send multiple notifications in batch."""
    for notification_id in notification_ids:
        send_notification.delay(notification_id)
    
    logger.info(f"Queued {len(notification_ids)} notifications for sending")

@shared_task
def send_bus_arrival_notifications(bus_id, estimated_time):
    """Send notifications about bus arrival."""
    from .models import Notification
    from buses.models import Bus
    from accounts.models import StudentProfile
    
    try:
        bus = Bus.objects.get(id=bus_id)
        students = StudentProfile.objects.filter(assigned_bus=bus)
        
        for student in students:
            Notification.objects.create(
                user=student.user,
                notification_type='bus_arrival',
                title=f'Bus {bus.bus_number} Arriving Soon',
                message=f'Your bus will arrive at {estimated_time.strftime("%I:%M %p")}',
                bus=bus,
                send_push=True,
                send_email=True if student.user.email else False
            )
        
        logger.info(f"Sent arrival notifications for bus {bus.bus_number}")
        
    except Exception as e:
        logger.error(f"Error sending arrival notifications: {str(e)}")

@shared_task
def send_delay_notifications(bus_id, delay_minutes, reason=""):
    """Send notifications about bus delays."""
    from .models import Notification
    from buses.models import Bus
    from accounts.models import StudentProfile
    
    try:
        bus = Bus.objects.get(id=bus_id)
        students = StudentProfile.objects.filter(assigned_bus=bus)
        
        message = f'Bus {bus.bus_number} is delayed by {delay_minutes} minutes'
        if reason:
            message += f' due to {reason}'
        
        for student in students:
            Notification.objects.create(
                user=student.user,
                notification_type='bus_delay',
                title='Bus Delay Alert',
                message=message,
                bus=bus,
                priority='high',
                send_push=True,
                send_sms=True  # Send SMS for delays
            )
        
        logger.info(f"Sent delay notifications for bus {bus.bus_number}")
        
    except Exception as e:
        logger.error(f"Error sending delay notifications: {str(e)}")

@shared_task
def send_emergency_notifications(bus_id, emergency_type, message):
    """Send emergency notifications."""
    from .models import Notification
    from buses.models import Bus
    from accounts.models import StudentProfile, DriverProfile
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        bus = Bus.objects.get(id=bus_id)
        
        # Notify students on the bus
        students = StudentProfile.objects.filter(assigned_bus=bus)
        for student in students:
            Notification.objects.create(
                user=student.user,
                notification_type='emergency',
                title=f'EMERGENCY ALERT: {emergency_type}',
                message=message,
                bus=bus,
                priority='urgent',
                send_push=True,
                send_sms=True,
                send_email=True
            )
        
        # Notify driver
        if hasattr(bus, 'driver') and bus.driver:
            Notification.objects.create(
                user=bus.driver.user,
                notification_type='emergency',
                title=f'EMERGENCY ALERT: {emergency_type}',
                message=message,
                bus=bus,
                priority='urgent',
                send_push=True,
                send_sms=True
            )
        
        # Notify admins
        admins = User.objects.filter(user_type='admin', is_active=True)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                notification_type='emergency',
                title=f'EMERGENCY ALERT: Bus {bus.bus_number}',
                message=f'{emergency_type}: {message}',
                bus=bus,
                priority='urgent',
                send_push=True,
                send_email=True
            )
        
        logger.info(f"Sent emergency notifications for bus {bus.bus_number}")
        
    except Exception as e:
        logger.error(f"Error sending emergency notifications: {str(e)}")