from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import NotificationPreference

User = get_user_model()

@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """
    Create notification preferences when a new user is created.
    """
    if created:
        NotificationPreference.objects.get_or_create(user=instance)

@receiver(post_save, sender='tracking.Trip')
def notify_trip_start(sender, instance, created, **kwargs):
    """
    Send notifications when a trip starts.
    """
    if created:
        from .tasks import send_bus_arrival_notifications
        # Schedule arrival notification
        send_bus_arrival_notifications.delay(instance.bus.id, instance.start_time)

@receiver(post_save, sender='tracking.Trip')
def notify_trip_end(sender, instance, **kwargs):
    """
    Send notifications when a trip ends.
    """
    if instance.status == 'completed' and instance.end_time:
        from .tasks import send_notification
        from .models import Notification
        from accounts.models import StudentProfile
        
        students = StudentProfile.objects.filter(assigned_bus=instance.bus)
        for student in students:
            Notification.objects.create(
                user=student.user,
                notification_type='bus_arrival',
                title='Trip Completed',
                message=f'Trip on bus {instance.bus.bus_number} has ended.',
                bus=instance.bus,
                trip=instance
            )