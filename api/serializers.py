from rest_framework import serializers
from accounts.models import User, StudentProfile, DriverProfile, ParentProfile
from buses.models import Bus, Route, Stop, Schedule
from tracking.models import LocationHistory, Trip, Geofence
from notifications.models import Notification

class UserSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'first_name', 'last_name',
            'user_type', 'user_type_display', 'is_active', 'is_verified',
            'profile_image', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    bus_number = serializers.CharField(source='assigned_bus.bus_number', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'full_name', 'email', 'roll_number', 'department',
            'year', 'semester', 'address', 'emergency_contact',
            'assigned_bus', 'bus_number', 'boarding_stop', 'qr_code'
        ]

class DriverProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    bus_number = serializers.CharField(source='assigned_bus.bus_number', read_only=True)
    
    class Meta:
        model = DriverProfile
        fields = [
            'id', 'user', 'full_name', 'license_number', 'experience',
            'address', 'emergency_contact', 'assigned_bus', 'bus_number',
            'is_active', 'license_expiry'
        ]

class BusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bus_type_display = serializers.CharField(source='get_bus_type_display', read_only=True)
    driver_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Bus
        fields = [
            'id', 'bus_number', 'registration_number', 'bus_type', 'bus_type_display',
            'capacity', 'current_latitude', 'current_longitude', 'current_speed',
            'fuel_level', 'status', 'status_display', 'is_tracking_enabled',
            'make', 'model', 'year', 'color', 'insurance_expiry', 'permit_expiry',
            'driver_name', 'student_count', 'last_updated', 'created_at'
        ]
        read_only_fields = ['last_updated', 'created_at']
    
    def get_driver_name(self, obj):
        if obj.driver:
            return obj.driver.user.get_full_name()
        return None
    
    def get_student_count(self, obj):
        return obj.students.count()

class RouteSerializer(serializers.ModelSerializer):
    stop_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Route
        fields = [
            'id', 'name', 'description', 'total_distance', 'estimated_duration',
            'is_active', 'stop_count', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_stop_count(self, obj):
        return obj.stops.count()

class StopSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source='route.name', read_only=True)
    
    class Meta:
        model = Stop
        fields = [
            'id', 'route', 'route_name', 'name', 'latitude', 'longitude',
            'sequence', 'estimated_arrival_time', 'is_pickup_point',
            'is_drop_point'
        ]

class ScheduleSerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_display', read_only=True)
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    route_name = serializers.CharField(source='route.name', read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'bus', 'bus_number', 'route', 'route_name', 'day', 'day_display',
            'departure_time', 'arrival_time', 'is_active'
        ]

class LocationHistorySerializer(serializers.ModelSerializer):
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    
    class Meta:
        model = LocationHistory
        fields = [
            'id', 'bus', 'bus_number', 'latitude', 'longitude', 'speed',
            'accuracy', 'battery_level', 'timestamp'
        ]
        read_only_fields = ['timestamp']

class TripSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    
    class Meta:
        model = Trip
        fields = [
            'id', 'bus', 'bus_number', 'schedule', 'start_time', 'end_time',
            'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude',
            'total_distance', 'average_speed', 'status', 'status_display',
            'passenger_count', 'created_at'
        ]
        read_only_fields = ['created_at']

class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'notification_type_display', 'title',
            'message', 'priority', 'priority_display', 'is_read', 'is_sent',
            'bus', 'route', 'time_ago', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
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