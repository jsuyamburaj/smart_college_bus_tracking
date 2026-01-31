from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta

from accounts.models import User, StudentProfile, DriverProfile, ParentProfile
from buses.models import Bus, Route, Stop, Schedule
from tracking.models import LocationHistory, Trip, Geofence
from notifications.models import Notification

from .serializers import (
    UserSerializer, StudentProfileSerializer, DriverProfileSerializer,
    BusSerializer, RouteSerializer, StopSerializer, ScheduleSerializer,
    LocationHistorySerializer, TripSerializer, NotificationSerializer
)
from accounts.permissions import (
    IsAdminUser, IsDriverUser, IsStudentUser, IsParentUser,
    IsProfileOwnerOrAdmin, IsAssignedDriver, IsAssignedStudent,
    CanTrackBus, HasBusAssignment
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsProfileOwnerOrAdmin]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return User.objects.all()
        else:
            return User.objects.filter(id=user.id)

class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsProfileOwnerOrAdmin]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

class DriverProfileViewSet(viewsets.ModelViewSet):
    queryset = DriverProfile.objects.all()
    serializer_class = DriverProfileSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsProfileOwnerOrAdmin]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

class BusViewSet(viewsets.ModelViewSet):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action == 'update_location':
            permission_classes = [IsDriverUser, IsAssignedDriver]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        """Update bus location (for drivers)."""
        bus = self.get_object()
        
        # Verify driver is assigned to this bus
        if request.user.driver_profile.assigned_bus != bus:
            return Response(
                {'error': 'You are not assigned to this bus'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        speed = request.data.get('speed', 0)
        
        if not latitude or not longitude:
            return Response(
                {'error': 'Latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update bus location
        bus.update_location(latitude, longitude, speed)
        
        # Create location history
        LocationHistory.objects.create(
            bus=bus,
            latitude=latitude,
            longitude=longitude,
            speed=speed
        )
        
        return Response({
            'success': True,
            'message': 'Location updated',
            'bus': BusSerializer(bus).data
        })
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active buses."""
        active_buses = Bus.objects.filter(status='active', is_tracking_enabled=True)
        serializer = self.get_serializer(active_buses, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def location_history(self, request, pk=None):
        """Get location history for a bus."""
        bus = self.get_object()
        
        # Check permission
        if not (request.user.user_type == 'admin' or 
                (request.user.user_type == 'student' and 
                 request.user.student_profile.assigned_bus == bus)):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get time range
        hours = request.GET.get('hours', 24)
        time_threshold = timezone.now() - timedelta(hours=int(hours))
        
        locations = LocationHistory.objects.filter(
            bus=bus,
            timestamp__gte=time_threshold
        ).order_by('timestamp')
        
        serializer = LocationHistorySerializer(locations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get students assigned to this bus."""
        bus = self.get_object()
        
        # Check permission
        if not (request.user.user_type == 'admin' or 
                request.user.user_type == 'driver' and 
                request.user.driver_profile.assigned_bus == bus):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        students = StudentProfile.objects.filter(assigned_bus=bus)
        serializer = StudentProfileSerializer(students, many=True)
        return Response(serializer.data)

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [IsAdminUser]

class StopViewSet(viewsets.ModelViewSet):
    queryset = Stop.objects.all()
    serializer_class = StopSerializer
    permission_classes = [IsAdminUser]

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's schedule."""
        today = datetime.now().strftime('%a').lower()[:3]
        schedules = Schedule.objects.filter(day=today, is_active=True)
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)

class LocationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LocationHistory.objects.all()
    serializer_class = LocationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'admin':
            return LocationHistory.objects.all()
        elif user.user_type == 'driver':
            try:
                bus = user.driver_profile.assigned_bus
                return LocationHistory.objects.filter(bus=bus)
            except:
                return LocationHistory.objects.none()
        elif user.user_type == 'student':
            try:
                bus = user.student_profile.assigned_bus
                return LocationHistory.objects.filter(bus=bus)
            except:
                return LocationHistory.objects.none()
        else:
            return LocationHistory.objects.none()

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a trip."""
        trip = self.get_object()
        
        if trip.status != 'scheduled':
            return Response(
                {'error': 'Trip cannot be started. Invalid status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        trip.status = 'in_progress'
        trip.start_time = timezone.now()
        
        # Set start location from bus current location
        if trip.bus.current_latitude and trip.bus.current_longitude:
            trip.start_latitude = trip.bus.current_latitude
            trip.start_longitude = trip.bus.current_longitude
        
        trip.save()
        
        # Create notification for students
        students = trip.bus.students.all()
        for student in students:
            Notification.objects.create(
                user=student.user,
                notification_type='bus_arrival',
                title=f'Trip Started - Bus {trip.bus.bus_number}',
                message=f'Your bus {trip.bus.bus_number} has started the trip.',
                bus=trip.bus,
                send_push=True
            )
        
        return Response({
            'success': True,
            'message': 'Trip started',
            'trip': TripSerializer(trip).data
        })
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End a trip."""
        trip = self.get_object()
        
        if trip.status != 'in_progress':
            return Response(
                {'error': 'Trip is not in progress.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        trip.status = 'completed'
        trip.end_time = timezone.now()
        
        # Set end location from bus current location
        if trip.bus.current_latitude and trip.bus.current_longitude:
            trip.end_latitude = trip.bus.current_latitude
            trip.end_longitude = trip.bus.current_longitude
        
        # Calculate total distance (simplified)
        # In production, you would calculate from trip points
        trip.total_distance = 0
        trip.average_speed = trip.bus.current_speed
        
        trip.save()
        
        return Response({
            'success': True,
            'message': 'Trip ended',
            'trip': TripSerializer(trip).data
        })

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications."""
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')
        
        page = self.paginate_queryset(notifications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'success': True})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({'success': True})

# Dashboard APIs
class DashboardAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        data = {}
        
        if user.user_type == 'admin':
            data = self.get_admin_dashboard()
        elif user.user_type == 'driver':
            data = self.get_driver_dashboard(user)
        elif user.user_type == 'student':
            data = self.get_student_dashboard(user)
        elif user.user_type == 'parent':
            data = self.get_parent_dashboard(user)
        
        return Response(data)
    
    def get_admin_dashboard(self):
        total_buses = Bus.objects.count()
        active_buses = Bus.objects.filter(status='active').count()
        total_students = StudentProfile.objects.count()
        total_drivers = DriverProfile.objects.count()
        total_routes = Route.objects.count()
        
        # Recent activities
        recent_locations = LocationHistory.objects.select_related('bus').order_by('-timestamp')[:10]
        recent_notifications = Notification.objects.select_related('user').order_by('-created_at')[:10]
        
        return {
            'stats': {
                'total_buses': total_buses,
                'active_buses': active_buses,
                'total_students': total_students,
                'total_drivers': total_drivers,
                'total_routes': total_routes,
            },
            'recent_locations': LocationHistorySerializer(recent_locations, many=True).data,
            'recent_notifications': NotificationSerializer(recent_notifications, many=True).data,
        }
    
    def get_driver_dashboard(self, user):
        try:
            driver_profile = user.driver_profile
            bus = driver_profile.assigned_bus
            
            if not bus:
                return {'error': 'No bus assigned'}
            
            # Today's schedule
            today = datetime.now().strftime('%a').lower()[:3]
            schedule = Schedule.objects.filter(bus=bus, day=today, is_active=True).first()
            
            # Current trip
            current_trip = Trip.objects.filter(bus=bus, status='in_progress').first()
            
            # Assigned students
            students = bus.students.all()[:10]
            
            return {
                'driver': DriverProfileSerializer(driver_profile).data,
                'bus': BusSerializer(bus).data,
                'schedule': ScheduleSerializer(schedule).data if schedule else None,
                'current_trip': TripSerializer(current_trip).data if current_trip else None,
                'students': StudentProfileSerializer(students, many=True).data,
                'current_location': {
                    'latitude': float(bus.current_latitude) if bus.current_latitude else None,
                    'longitude': float(bus.current_longitude) if bus.current_longitude else None,
                    'speed': bus.current_speed,
                } if bus.current_latitude else None,
            }
        except DriverProfile.DoesNotExist:
            return {'error': 'Driver profile not found'}
    
    def get_student_dashboard(self, user):
        try:
            student_profile = user.student_profile
            bus = student_profile.assigned_bus
            
            if not bus:
                return {'error': 'No bus assigned'}
            
            # Today's schedule
            today = datetime.now().strftime('%a').lower()[:3]
            schedule = Schedule.objects.filter(bus=bus, day=today, is_active=True).first()
            
            # Bus location
            bus_location = None
            if bus.current_latitude and bus.current_longitude:
                bus_location = {
                    'latitude': float(bus.current_latitude),
                    'longitude': float(bus.current_longitude),
                    'speed': bus.current_speed,
                }
            
            # Estimated arrival
            estimated_arrival = None
            if bus_location and student_profile.boarding_stop:
                # Simplified calculation
                estimated_arrival = timezone.now() + timedelta(minutes=15)
            
            return {
                'student': StudentProfileSerializer(student_profile).data,
                'bus': BusSerializer(bus).data,
                'schedule': ScheduleSerializer(schedule).data if schedule else None,
                'bus_location': bus_location,
                'estimated_arrival': estimated_arrival.isoformat() if estimated_arrival else None,
                'boarding_stop': {
                    'id': student_profile.boarding_stop.id,
                    'name': student_profile.boarding_stop.name,
                } if student_profile.boarding_stop else None,
            }
        except StudentProfile.DoesNotExist:
            return {'error': 'Student profile not found'}
    
    def get_parent_dashboard(self, user):
        try:
            parent_profile = user.parent_profile
            student = parent_profile.student
            bus = student.assigned_bus
            
            return {
                'parent': {
                    'user': user.username,
                    'relationship': parent_profile.relationship,
                },
                'student': StudentProfileSerializer(student).data,
                'bus': BusSerializer(bus).data if bus else None,
                'bus_location': {
                    'latitude': float(bus.current_latitude) if bus and bus.current_latitude else None,
                    'longitude': float(bus.current_longitude) if bus and bus.current_longitude else None,
                } if bus else None,
            }
        except ParentProfile.DoesNotExist:
            return {'error': 'Parent profile not found'}

# Public APIs (no authentication required)
class BusLocationsAPI(APIView):
    """Public API to get all bus locations."""
    
    def get(self, request):
        buses = Bus.objects.filter(
            is_tracking_enabled=True,
            status='active'
        ).exclude(
            Q(current_latitude__isnull=True) | Q(current_longitude__isnull=True)
        )
        
        locations = []
        for bus in buses:
            locations.append({
                'bus_id': bus.id,
                'bus_number': bus.bus_number,
                'latitude': float(bus.current_latitude),
                'longitude': float(bus.current_longitude),
                'speed': bus.current_speed,
                'status': bus.status,
                'driver': bus.driver.user.get_full_name() if bus.driver else None,
                'last_updated': bus.last_updated.isoformat() if bus.last_updated else None,
            })
        
        return Response({'locations': locations})

class RouteStopsAPI(APIView):
    """Public API to get stops for a route."""
    
    def get(self, request, route_id):
        route = get_object_or_404(Route, id=route_id)
        stops = Stop.objects.filter(route=route).order_by('sequence')
        
        serializer = StopSerializer(stops, many=True)
        return Response({
            'route': RouteSerializer(route).data,
            'stops': serializer.data
        })