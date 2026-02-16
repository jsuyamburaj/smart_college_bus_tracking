from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('bus_arrival', 'Bus Arrival'),
        ('bus_delay', 'Bus Delay'),
        ('emergency', 'Emergency'),
        ('route_change', 'Route Change'),
        ('maintenance', 'Maintenance'),
        ('announcement', 'Announcement'),
        ('reminder', 'Reminder'),
        ('system', 'System'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Related objects (optional)
    bus = models.ForeignKey('buses.Bus', on_delete=models.SET_NULL, null=True, blank=True)
    route = models.ForeignKey('buses.Route', on_delete=models.SET_NULL, null=True, blank=True)
    trip = models.ForeignKey('tracking.Trip', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status fields
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery methods
    send_email = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    send_push = models.BooleanField(default=True)
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['scheduled_for']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.username} - {self.created_at}"
    
    def save(self, *args, **kwargs):
        if self.is_read and not self.read_at:
            self.read_at = timezone.now()
        super().save(*args, **kwargs)
    
    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_sent(self):
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=['is_sent', 'sent_at'])

class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email preferences
    email_bus_arrival = models.BooleanField(default=True)
    email_bus_delay = models.BooleanField(default=True)
    email_emergency = models.BooleanField(default=True)
    email_route_change = models.BooleanField(default=True)
    email_maintenance = models.BooleanField(default=False)
    email_announcements = models.BooleanField(default=True)
    email_system = models.BooleanField(default=False)
    
    # SMS preferences
    sms_bus_arrival = models.BooleanField(default=False)
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
    push_system = models.BooleanField(default=False)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True, default='22:00')
    quiet_hours_end = models.TimeField(null=True, blank=True, default='07:00')
    
    # Rate limiting
    max_notifications_per_hour = models.IntegerField(default=10)
    max_emails_per_day = models.IntegerField(default=5)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences - {self.user.username}"
    
    def should_send(self, notification_type, delivery_method):
        """Check if a notification should be sent based on preferences"""
        if delivery_method == 'email':
            pref_map = {
                'bus_arrival': self.email_bus_arrival,
                'bus_delay': self.email_bus_delay,
                'emergency': self.email_emergency,
                'route_change': self.email_route_change,
                'maintenance': self.email_maintenance,
                'announcement': self.email_announcements,
                'system': self.email_system,
            }
        elif delivery_method == 'sms':
            pref_map = {
                'bus_arrival': self.sms_bus_arrival,
                'bus_delay': self.sms_bus_delay,
                'emergency': self.sms_emergency,
                'route_change': self.sms_route_change,
            }
        elif delivery_method == 'push':
            pref_map = {
                'bus_arrival': self.push_bus_arrival,
                'bus_delay': self.push_bus_delay,
                'emergency': self.push_emergency,
                'route_change': self.push_route_change,
                'maintenance': self.push_maintenance,
                'announcement': self.push_announcements,
                'system': self.push_system,
            }
        else:
            return False
        
        return pref_map.get(notification_type, False)

class NotificationLog(models.Model):
    """Log of sent notifications for tracking"""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    delivery_method = models.CharField(max_length=10, choices=(
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push'),
    ))
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ), default='pending')
    
    # Provider information
    provider = models.CharField(max_length=50, blank=True)
    provider_message_id = models.CharField(max_length=100, blank=True)
    
    # Error tracking
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # Timing
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['delivery_method']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.delivery_method} - {self.status} - {self.created_at}"
    
    def mark_sent(self, provider_message_id=None):
        self.status = 'sent'
        self.sent_at = timezone.now()
        if provider_message_id:
            self.provider_message_id = provider_message_id
        self.save(update_fields=['status', 'sent_at', 'provider_message_id'])
    
    def mark_delivered(self):
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_failed(self, error_code, error_message):
        self.status = 'failed'
        self.error_code = error_code
        self.error_message = error_message
        self.save(update_fields=['status', 'error_code', 'error_message'])

class NotificationTemplate(models.Model):
    """Templates for notifications"""
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.CharField(max_length=20, choices=Notification.NOTIFICATION_TYPES)
    
    # Templates for different formats
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    email_subject_template = models.CharField(max_length=200, blank=True)
    email_body_template = models.TextField(blank=True)
    sms_template = models.TextField(blank=True)
    push_template = models.TextField(blank=True)
    
    # Variables expected in the template
    variables = models.JSONField(default=list, help_text="List of variables expected in the template")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
    
    def __str__(self):
        return f"{self.name} - {self.get_notification_type_display()}"
    
    def render(self, context):
        """Render the template with given context"""
        from django.template import Template, Context
        
        title_template = Template(self.title_template)
        message_template = Template(self.message_template)
        
        context_obj = Context(context)
        
        return {
            'title': title_template.render(context_obj),
            'message': message_template.render(context_obj),
            'email_subject': Template(self.email_subject_template).render(context_obj) if self.email_subject_template else None,
            'email_body': Template(self.email_body_template).render(context_obj) if self.email_body_template else None,
            'sms': Template(self.sms_template).render(context_obj) if self.sms_template else None,
            'push': Template(self.push_template).render(context_obj) if self.push_template else None,
        }