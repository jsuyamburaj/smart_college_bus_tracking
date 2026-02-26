from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from accounts.models import User, StudentProfile, DriverProfile, ParentProfile
from buses.models import Bus, Route, Stop, Schedule, BusMaintenance
from tracking.models import Issue, LocationHistory, Trip, TripPoint, Geofence, GeofenceEvent
from notifications.models import Notification, NotificationPreference

User = get_user_model()

# ==================== User Serializers ====================

class UserSerializer(serializers.ModelSerializer):
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'first_name', 'last_name', 'full_name',
            'user_type', 'user_type_display', 'profile_image', 'is_verified',
            'is_active', 'last_login', 'date_joined', 'created_at'
        ]
        read_only_fields = ['id', 'last_login', 'date_joined', 'created_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name()

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'phone', 'first_name', 'last_name',
            'user_type', 'password', 'password2'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate email uniqueness
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})
        
        # Validate phone uniqueness
        if User.objects.filter(phone=attrs['phone']).exists():
            raise serializers.ValidationError({"phone": "This phone number is already in use."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validatedData)
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_image']
    
    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value
    
    def validate_phone(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(phone=value).exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            from django.contrib.auth import authenticate
            user = authenticate(username=username, password=password)
            
            if not user:
                # Try with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if not user:
                raise serializers.ValidationError('Unable to log in with provided credentials.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "username" and "password".')

# ==================== Student Profile Serializers ====================

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    bus_number = serializers.CharField(source='assigned_bus.bus_number', read_only=True)
    boarding_stop_name = serializers.CharField(source='boarding_stop.name', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'full_name', 'email', 'phone', 'roll_number',
            'department', 'year', 'semester', 'address', 'emergency_contact',
            'assigned_bus', 'bus_number', 'boarding_stop', 'boarding_stop_name',
            'qr_code', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class StudentProfileCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer()
    
    class Meta:
        model = StudentProfile
        fields = [
            'user', 'roll_number', 'department', 'year', 'semester',
            'address', 'emergency_contact', 'assigned_bus', 'boarding_stop'
        ]
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['user_type'] = 'student'
        
        user_serializer = UserCreateSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        student = StudentProfile.objects.create(user=user, **validated_data)
        return student

# ==================== Driver Profile Serializers ====================

class DriverProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    bus_number = serializers.CharField(source='assigned_bus.bus_number', read_only=True)
    
    class Meta:
        model = DriverProfile
        fields = [
            'id', 'user', 'full_name', 'email', 'phone', 'license_number',
            'experience', 'address', 'emergency_contact', 'assigned_bus',
            'bus_number', 'is_active', 'license_expiry', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class DriverProfileCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer()
    
    class Meta:
        model = DriverProfile
        fields = [
            'user', 'license_number', 'experience', 'address',
            'emergency_contact', 'assigned_bus', 'license_expiry'
        ]
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['user_type'] = 'driver'
        
        user_serializer = UserCreateSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        driver = DriverProfile.objects.create(user=user, **validated_data)
        return driver

# ==================== Parent Profile Serializers ====================

class ParentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    student_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ParentProfile
        fields = [
            'id', 'user', 'full_name', 'email', 'phone', 'student',
            'student_details', 'relationship', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_student_details(self, obj):
        if obj.student:
            return {
                'id': obj.student.id,
                'name': obj.student.user.get_full_name(),
                'roll_number': obj.student.roll_number,
                'department': obj.student.department,
                'year': obj.student.year,
                'bus': obj.student.assigned_bus.bus_number if obj.student.assigned_bus else None
            }
        return None

class ParentProfileCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer()
    
    class Meta:
        model = ParentProfile
        fields = ['user', 'student', 'relationship']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['user_type'] = 'parent'
        
        user_serializer = UserCreateSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        parent = ParentProfile.objects.create(user=user, **validated_data)
        return parent

# ==================== Bus Serializers ====================

class BusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bus_type_display = serializers.CharField(source='get_bus_type_display', read_only=True)
    driver_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    current_location = serializers.SerializerMethodField()
    
    class Meta:
        model = Bus
        fields = [
            'id', 'bus_number', 'registration_number', 'bus_type', 'bus_type_display',
            'capacity', 'current_latitude', 'current_longitude', 'current_location',
            'current_speed', 'fuel_level', 'status', 'status_display', 'is_tracking_enabled',
            'make', 'model', 'year', 'color', 'insurance_expiry', 'permit_expiry',
            'driver_name', 'student_count', 'last_updated', 'created_at'
        ]
        read_only_fields = ['last_updated', 'created_at']
    
    def get_driver_name(self, obj):
        if hasattr(obj, 'driver') and obj.driver:
            return obj.driver.user.get_full_name()
        return None
    
    def get_student_count(self, obj):
        return obj.students.count()
    
    def get_current_location(self, obj):
        if obj.current_latitude and obj.current_longitude:
            return {
                'latitude': float(obj.current_latitude),
                'longitude': float(obj.current_longitude)
            }
        return None

class BusLocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    speed = serializers.FloatField(required=False, default=0)
    fuel_level = serializers.FloatField(required=False, min_value=0, max_value=100)
    
    def validate(self, attrs):
        lat = attrs.get('latitude')
        lng = attrs.get('longitude')
        
        if lat < -90 or lat > 90:
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        
        if lng < -180 or lng > 180:
            raise serializers.ValidationError({"longitude": "Longitude must be between -180 and 180."})
        
        return attrs

# ==================== Route & Stop Serializers ====================

class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = [
            'id', 'route', 'name', 'latitude', 'longitude', 'sequence',
            'estimated_arrival_time', 'is_pickup_point', 'is_drop_point'
        ]

class RouteSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)
    stop_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Route
        fields = [
            'id', 'name', 'description', 'total_distance', 'estimated_duration',
            'is_active', 'stops', 'stop_count', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_stop_count(self, obj):
        return obj.stops.count()

class RouteDetailSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id', 'name', 'description', 'total_distance', 'estimated_duration',
            'is_active', 'stops', 'created_at'
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

class BusMaintenanceSerializer(serializers.ModelSerializer):
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    
    class Meta:
        model = BusMaintenance
        fields = [
            'id', 'bus', 'bus_number', 'maintenance_date', 'maintenance_type',
            'description', 'cost', 'next_maintenance_date', 'performed_by', 'created_at'
        ]
        read_only_fields = ['created_at']

# ==================== Tracking Serializers ====================

class LocationHistorySerializer(serializers.ModelSerializer):
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = LocationHistory
        fields = [
            'id', 'bus', 'bus_number', 'latitude', 'longitude', 'speed',
            'accuracy', 'battery_level', 'timestamp', 'time_ago'
        ]
        read_only_fields = ['timestamp']
    
    def get_time_ago(self, obj):
        from datetime import datetime
        now = timezone.now()
        diff = now - obj.timestamp
        
        if diff.days > 0:
            return f"{diff.days} day(s) ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour(s) ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute(s) ago"
        else:
            return "Just now"

class TripPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripPoint
        fields = ['id', 'trip', 'latitude', 'longitude', 'sequence', 'timestamp', 'speed']

class TripSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    driver_name = serializers.SerializerMethodField()
    points = TripPointSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trip
        fields = [
            'id', 'bus', 'bus_number', 'driver_name', 'schedule', 'start_time', 'end_time',
            'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude',
            'total_distance', 'average_speed', 'status', 'status_display',
            'passenger_count', 'points', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_driver_name(self, obj):
        if hasattr(obj.bus, 'driver') and obj.bus.driver:
            return obj.bus.driver.user.get_full_name()
        return None

class TripCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = [
            'bus', 'schedule', 'start_time', 'start_latitude', 'start_longitude',
            'passenger_count'
        ]
    
    def validate(self, attrs):
        # Check if there's already an active trip for this bus
        bus = attrs.get('bus')
        if Trip.objects.filter(bus=bus, status='in_progress').exists():
            raise serializers.ValidationError("This bus already has an active trip.")
        return attrs

class GeofenceSerializer(serializers.ModelSerializer):
    geofence_type_display = serializers.CharField(source='get_geofence_type_display', read_only=True)
    
    class Meta:
        model = Geofence
        fields = [
            'id', 'name', 'geofence_type', 'geofence_type_display',
            'center_latitude', 'center_longitude', 'radius', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']

class GeofenceEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    geofence_name = serializers.CharField(source='geofence.name', read_only=True)
    
    class Meta:
        model = GeofenceEvent
        fields = [
            'id', 'bus', 'bus_number', 'geofence', 'geofence_name',
            'event_type', 'event_type_display', 'latitude', 'longitude', 'timestamp'
        ]
        read_only_fields = ['timestamp']

# ==================== Notification Serializers ====================

class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    route_name = serializers.CharField(source='route.name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'notification_type_display',
            'title', 'message', 'priority', 'priority_display',
            'bus', 'bus_number', 'route', 'route_name', 'is_read',
            'is_sent', 'created_at', 'time_ago'
        ]
        read_only_fields = ['created_at']
    
    def get_time_ago(self, obj):
        from datetime import datetime
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day(s) ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour(s) ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute(s) ago"
        else:
            return "Just now"

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        exclude = ['id', 'user', 'updated_at']

class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'user', 'notification_type', 'title', 'message', 'priority',
            'bus', 'route', 'send_email', 'send_sms', 'send_push', 'scheduled_for'
        ]

# ==================== Dashboard Serializers ====================

class AdminDashboardSerializer(serializers.Serializer):
    total_buses = serializers.IntegerField()
    active_buses = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_drivers = serializers.IntegerField()
    total_routes = serializers.IntegerField()
    active_trips = serializers.IntegerField()
    recent_activities = serializers.ListField(child=serializers.DictField())
    recent_notifications = serializers.ListField(child=serializers.DictField())

class DriverDashboardSerializer(serializers.Serializer):
    driver_info = DriverProfileSerializer()
    bus_info = BusSerializer()
    today_schedule = ScheduleSerializer(allow_null=True)
    current_trip = TripSerializer(allow_null=True)
    assigned_students = StudentProfileSerializer(many=True)
    recent_locations = LocationHistorySerializer(many=True)

class StudentDashboardSerializer(serializers.Serializer):
    student_info = StudentProfileSerializer()
    bus_info = BusSerializer(allow_null=True)
    today_schedule = ScheduleSerializer(allow_null=True)
    bus_location = serializers.DictField(allow_null=True)
    estimated_arrival = serializers.DateTimeField(allow_null=True)
    recent_notifications = NotificationSerializer(many=True)

class ParentDashboardSerializer(serializers.Serializer):
    parent_info = ParentProfileSerializer()
    student_info = StudentProfileSerializer()
    bus_info = BusSerializer(allow_null=True)
    bus_location = serializers.DictField(allow_null=True)
    recent_notifications = NotificationSerializer(many=True)

# ==================== Public Serializers ====================

class PublicBusLocationSerializer(serializers.Serializer):
    bus_id = serializers.IntegerField()
    bus_number = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    speed = serializers.FloatField()
    status = serializers.CharField()
    driver = serializers.CharField(allow_null=True)
    last_updated = serializers.DateTimeField()

class PublicStatsSerializer(serializers.Serializer):
    total_buses = serializers.IntegerField()
    active_buses = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_drivers = serializers.IntegerField()
    total_routes = serializers.IntegerField()
    active_trips = serializers.IntegerField()
    on_time_rate = serializers.FloatField()

# ==================== Analytics Serializers ====================

class TripAnalyticsSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_trips = serializers.IntegerField()
    completed_trips = serializers.IntegerField()
    cancelled_trips = serializers.IntegerField()
    average_duration = serializers.DurationField()
    average_distance = serializers.FloatField()
    total_passengers = serializers.IntegerField()

class BusAnalyticsSerializer(serializers.Serializer):
    bus_id = serializers.IntegerField()
    bus_number = serializers.CharField()
    total_trips = serializers.IntegerField()
    total_distance = serializers.FloatField()
    average_speed = serializers.FloatField()
    fuel_consumed = serializers.FloatField()
    maintenance_count = serializers.IntegerField()

class StudentAnalyticsSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    roll_number = serializers.CharField()
    total_trips = serializers.IntegerField()
    on_time_arrivals = serializers.IntegerField()
    late_arrivals = serializers.IntegerField()
    attendance_rate = serializers.FloatField()

# ==================== Password & Auth Serializers ====================

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(required=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Passwords don't match."})
        
        if len(attrs['new_password']) < 8:
            raise serializers.ValidationError({"new_password": "Password must be at least 8 characters."})
        
        return attrs

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(required=True, style={'input_type': 'password'})
    token = serializers.CharField(required=True)
    uid = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Passwords don't match."})
        return attrs

class IssueSerializer(serializers.ModelSerializer):
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    route_name = serializers.CharField(source='route.name', read_only=True)
    reported_by_name = serializers.CharField(source='reported_by.get_full_name', read_only=True)
    
    class Meta:
        model = Issue
        fields = [
            'id', 'bus', 'bus_number', 'route', 'route_name',
            'reported_by', 'reported_by_name', 'issue_type',
            'description', 'status', 'created_at'
        ]
        read_only_fields = ['created_at']