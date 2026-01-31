from django.db import models
from accounts.models import User

class Bus(models.Model):
    BUS_TYPE_CHOICES = (
        ('ac', 'AC Bus'),
        ('non_ac', 'Non-AC Bus'),
        ('sleeper', 'Sleeper Bus'),
        ('mini', 'Mini Bus'),
    )
    
    BUS_STATUS_CHOICES = (
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    )
    
    bus_number = models.CharField(max_length=20, unique=True)
    registration_number = models.CharField(max_length=50, unique=True)
    bus_type = models.CharField(max_length=20, choices=BUS_TYPE_CHOICES)
    capacity = models.IntegerField()
    
    # Location fields (NO GIS)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_speed = models.FloatField(default=0)  # km/h
    
    fuel_level = models.FloatField(default=100)  # percentage
    status = models.CharField(max_length=20, choices=BUS_STATUS_CHOICES, default='active')
    is_tracking_enabled = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Bus details
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    color = models.CharField(max_length=50)
    insurance_expiry = models.DateField()
    permit_expiry = models.DateField()
    
    def __str__(self):
        return f"{self.bus_number} - {self.registration_number}"
    
    def update_location(self, latitude, longitude, speed=0):
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.current_speed = speed
        self.save()

class Route(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    total_distance = models.FloatField(help_text="Distance in kilometers")
    estimated_duration = models.DurationField(help_text="Estimated travel time")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Stop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=100)
    
    # Location fields (NO GIS)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    sequence = models.IntegerField()
    estimated_arrival_time = models.TimeField()
    is_pickup_point = models.BooleanField(default=True)
    is_drop_point = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['sequence']
    
    def __str__(self):
        return f"{self.name} (Stop #{self.sequence})"

class Schedule(models.Model):
    DAY_CHOICES = (
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    )
    
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='schedules')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='schedules')
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.bus.bus_number} - {self.route.name} ({self.day})"
class BusMaintenance(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='maintenance_records')
    maintenance_date = models.DateField()
    maintenance_type = models.CharField(max_length=100)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    next_maintenance_date = models.DateField()
    performed_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)  # ADD THIS LINE
    
    def __str__(self):
        return f"{self.bus.bus_number} - {self.maintenance_type} ({self.maintenance_date})"
    
    class Meta:
        ordering = ['-maintenance_date']    