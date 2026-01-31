from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('bus_arrival', 'Bus Arrival'),
        ('bus_delay', 'Bus Delay'),
        ('emergency', 'Emergency'),
        ('route_change', 'Route Change'),
        ('maintenance', 'Maintenance'),
        ('announcement', 'Announcement'),
        ('reminder', 'Reminder'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Related objects (optional)
    bus = models.ForeignKey('buses.Bus', on_delete=models.SET_NULL, null=True, blank=True)
    route = models.ForeignKey('buses.Route', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status fields
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    
    # Delivery methods
    send_email = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    send_push = models.BooleanField(default=True)
    
    # Timestamps
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['scheduled_for']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.username}"

class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_bus_arrival = models.BooleanField(default=True)
    email_bus_delay = models.BooleanField(default=True)
    email_emergency = models.BooleanField(default=True)
    email_route_change = models.BooleanField(default=True)
    email_maintenance = models.BooleanField(default=False)
    email_announcements = models.BooleanField(default=True)
    
    # SMS preferences
    sms_bus_arrival = models.BooleanField(default=True)
    sms_bus_delay = models.BooleanField(default=True)
    sms_emergency = models.BooleanField(default=True)
    sms_route_change = models.BooleanField(default=False)
    
    # Push notification preferences
    push_bus_arrival = models.BooleanField(default=True)
    push_bus_delay = models.BooleanField(default=True)
    push_emergency = models.BooleanField(default=True)
    push_route_change = models.BooleanField(default=True)
    push_maintenance = models.BooleanField(default=True)
    push_announcements = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True, default='22:00')
    quiet_hours_end = models.TimeField(null=True, blank=True, default='07:00')
    respect_quiet_hours = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences - {self.user.username}"

class SMSLog(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    )
    
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='sms_logs')
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_message_id = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"SMS to {self.phone_number} - {self.status}"

class EmailLog(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    )
    
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='email_logs')
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_message_id = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Email to {self.email} - {self.status}"