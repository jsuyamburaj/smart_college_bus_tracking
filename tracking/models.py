from django.db import models
from buses.models import Bus
from accounts.models import DriverProfile
from django.conf import settings
from django.utils import timezone
# from django.utils import timezone


class LocationHistory(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='location_history')
    
    # Location fields (NO GIS)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    speed = models.FloatField(default=0)  # km/h
    accuracy = models.FloatField(null=True, blank=True)  # GPS accuracy in meters
    battery_level = models.FloatField(null=True, blank=True)  # Device battery percentage
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['bus', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.bus.bus_number} - {self.timestamp}"

class Geofence(models.Model):
    GEOFENCE_TYPE_CHOICES = (
        ('school', 'School'),
        ('stop', 'Bus Stop'),
        ('zone', 'Zone'),
        ('restricted', 'Restricted Area'),
    )
    
    name = models.CharField(max_length=100)
    geofence_type = models.CharField(max_length=20, choices=GEOFENCE_TYPE_CHOICES)
    
    # Center point of geofence (NO GIS Polygon)
    center_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    center_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    radius = models.FloatField(help_text="Radius in meters")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_geofence_type_display()})"

class GeofenceEvent(models.Model):
    EVENT_TYPE_CHOICES = (
        ('entry', 'Entry'),
        ('exit', 'Exit'),
        ('inside', 'Inside'),
    )
    
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='geofence_events')
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    
    # Location where event occurred
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.bus.bus_number} - {self.event_type} - {self.geofence.name}"

class Trip(models.Model):
    TRIP_STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('delayed', 'Delayed'),
    )

    driver = models.ForeignKey('accounts.DriverProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')    
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='trips')
    schedule = models.ForeignKey('buses.Schedule', on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Start location
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # End location
    end_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    end_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    total_distance = models.FloatField(default=0)  # in kilometers
    average_speed = models.FloatField(default=0)  # km/h
    status = models.CharField(max_length=20, choices=TRIP_STATUS_CHOICES, default='scheduled')
    passenger_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.bus.bus_number} - {self.start_time.date()}"

class TripPoint(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='points')
    
    # Location point
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    sequence = models.IntegerField()
    timestamp = models.DateTimeField()
    speed = models.FloatField(default=0)
    
    class Meta:
        ordering = ['sequence']

class BusLocation(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bus} - {self.latitude}, {self.longitude}"

# Add this to tracking/models.py

class Issue(models.Model):
    """
    Model for reporting issues (by drivers, students, etc.)
    """
    ISSUE_STATUS_CHOICES = (
        ('reported', 'Reported'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    ISSUE_PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    
    ISSUE_TYPE_CHOICES = (
        ('mechanical', 'Mechanical Issue'),
        ('accident', 'Accident'),
        ('delay', 'Delay'),
        ('route_deviation', 'Route Deviation'),
        ('student_issue', 'Student Issue'),
        ('traffic', 'Traffic'),
        ('weather', 'Weather'),
        ('other', 'Other'),
    )
    
    # Basic info
    title = models.CharField(max_length=200)
    description = models.TextField()
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=ISSUE_PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=ISSUE_STATUS_CHOICES, default='reported')
    
    # Related objects
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_issues'
    )
    bus = models.ForeignKey('buses.Bus', on_delete=models.SET_NULL, null=True, blank=True)
    trip = models.ForeignKey('Trip', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Location where issue occurred
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Media attachments
    image = models.ImageField(upload_to='issues/', null=True, blank=True)
    
    # Resolution
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_issues'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['issue_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Issue #{self.id}: {self.title}"
    
    def resolve(self, user, notes):
        self.status = 'resolved'
        self.resolution_notes = notes
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()
        
        # Send notification
        from notifications.models import Notification
        Notification.objects.create(
            user=self.reported_by,
            notification_type='system',
            title='Issue Resolved',
            message=f'Your issue "{self.title}" has been resolved.',
            priority='medium'
        )

class IssueComment(models.Model):
    """
    Comments on issues for tracking progress
    """
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on Issue #{self.issue.id} by {self.user.username}"