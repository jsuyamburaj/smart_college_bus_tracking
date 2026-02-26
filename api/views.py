from rest_framework import viewsets, status, generics, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout

from accounts.models import User, StudentProfile, DriverProfile, ParentProfile
from buses.models import Bus, Route, Stop, Schedule, BusMaintenance
from tracking.models import LocationHistory, Trip, TripPoint, Geofence, GeofenceEvent, Issue
from notifications.models import Notification, NotificationPreference

from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer, UserLoginSerializer,
    StudentProfileSerializer, StudentProfileCreateSerializer,
    DriverProfileSerializer, DriverProfileCreateSerializer,
    ParentProfileSerializer, ParentProfileCreateSerializer,
    BusSerializer, BusLocationUpdateSerializer,
    RouteSerializer, RouteDetailSerializer, StopSerializer, ScheduleSerializer,
    BusMaintenanceSerializer,
    LocationHistorySerializer, TripSerializer, TripCreateSerializer,
    GeofenceSerializer, GeofenceEventSerializer,
    NotificationSerializer, NotificationCreateSerializer, NotificationPreferenceSerializer,
    AdminDashboardSerializer, DriverDashboardSerializer, StudentDashboardSerializer,
    PublicBusLocationSerializer, PublicStatsSerializer,
    PasswordChangeSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer,IssueSerializer
)

from .permissions import (
    IsAdminUser, IsDriverUser, IsStudentUser, IsParentUser,
    IsOwnerOrReadOnly, IsAssignedDriver, CanAccessBusLocation,
    CanUpdateLocation, CanCreateTrip, CanViewReports, IsVerifiedUser
)

# ==================== Authentication Views ====================

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            
            # Return user data
            user_serializer = UserSerializer(user)
            return Response({
                'success': True,
                'message': 'Login successful',
                'user': user_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({
            'success': True,
            'message': 'Logout successful'
        })

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_type = request.data.get('user_type')
        
        if user_type == 'student':
            serializer = StudentProfileCreateSerializer(data=request.data)
        elif user_type == 'driver':
            serializer = DriverProfileCreateSerializer(data=request.data)
        elif user_type == 'parent':
            serializer = ParentProfileCreateSerializer(data=request.data)
        else:
            return Response({
                'error': 'Invalid user type'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if serializer.is_valid():
            instance = serializer.save()
            
            # Auto login after registration
            user = instance.user if hasattr(instance, 'user') else instance
            login(request, user)
            
            return Response({
                'success': True,
                'message': 'Registration successful',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

# ==================== User Views ====================

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Filter by user type
        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search)
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'user': UserSerializer(request.user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({
                    'success': True,
                    'message': 'Password changed successfully'
                })
            else:
                return Response({
                    'error': 'Old password is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==================== Student Profile Views ====================

class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.select_related('user', 'assigned_bus', 'boarding_stop')
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StudentProfileCreateSerializer
        return StudentProfileSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department=department)
        
        # Filter by year
        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)
        
        # Filter by bus
        bus_id = self.request.query_params.get('bus')
        if bus_id:
            queryset = queryset.filter(assigned_bus_id=bus_id)
        
        return queryset
    
    @action(detail=False, methods=['get'], permission_classes=[IsStudentUser])
    def my_profile(self, request):
        try:
            profile = request.user.student_profile
            serializer = StudentProfileSerializer(profile)
            return Response(serializer.data)
        except StudentProfile.DoesNotExist:
            return Response({
                'error': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_bus(self, request, pk=None):
        student = self.get_object()
        bus_id = request.data.get('bus_id')
        
        if bus_id:
            try:
                bus = Bus.objects.get(id=bus_id)
                student.assigned_bus = bus
                student.save()
                
                # Send notification to student
                Notification.objects.create(
                    user=student.user,
                    notification_type='announcement',
                    title='Bus Assignment Updated',
                    message=f'You have been assigned to bus {bus.bus_number}',
                    bus=bus
                )
                
                return Response({
                    'success': True,
                    'message': f'Student assigned to bus {bus.bus_number}'
                })
            except Bus.DoesNotExist:
                return Response({
                    'error': 'Bus not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'error': 'Bus ID required'
        }, status=status.HTTP_400_BAD_REQUEST)

# ==================== Driver Profile Views ====================

class DriverProfileViewSet(viewsets.ModelViewSet):
    queryset = DriverProfile.objects.select_related('user', 'assigned_bus')
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DriverProfileCreateSerializer
        return DriverProfileSerializer
    
    @action(detail=False, methods=['get'], permission_classes=[IsDriverUser])
    def my_profile(self, request):
        try:
            profile = request.user.driver_profile
            serializer = DriverProfileSerializer(profile)
            return Response(serializer.data)
        except DriverProfile.DoesNotExist:
            return Response({
                'error': 'Driver profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_bus(self, request, pk=None):
        driver = self.get_object()
        bus_id = request.data.get('bus_id')
        
        if bus_id:
            try:
                bus = Bus.objects.get(id=bus_id)
                
                # Check if bus already has a driver
                if hasattr(bus, 'driver') and bus.driver:
                    return Response({
                        'error': 'Bus already has a driver assigned'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                driver.assigned_bus = bus
                driver.save()
                
                # Send notification to driver
                Notification.objects.create(
                    user=driver.user,
                    notification_type='announcement',
                    title='Bus Assignment Updated',
                    message=f'You have been assigned to bus {bus.bus_number}',
                    bus=bus
                )
                
                return Response({
                    'success': True,
                    'message': f'Driver assigned to bus {bus.bus_number}'
                })
            except Bus.DoesNotExist:
                return Response({
                    'error': 'Bus not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'error': 'Bus ID required'
        }, status=status.HTTP_400_BAD_REQUEST)

# ==================== Parent Profile Views ====================

class ParentProfileViewSet(viewsets.ModelViewSet):
    queryset = ParentProfile.objects.select_related('user', 'student')
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ParentProfileCreateSerializer
        return ParentProfileSerializer
    
    @action(detail=False, methods=['get'], permission_classes=[IsParentUser])
    def my_profile(self, request):
        try:
            profile = request.user.parent_profile
            serializer = ParentProfileSerializer(profile)
            return Response(serializer.data)
        except ParentProfile.DoesNotExist:
            return Response({
                'error': 'Parent profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

# ==================== Bus Views ====================

class BusViewSet(viewsets.ModelViewSet):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        elif self.action in ['update_location']:
            return [IsAuthenticated(), CanUpdateLocation()]
        elif self.action in ['current_trip', 'location_history']:
            return [IsAuthenticated(), CanAccessBusLocation()]
        return [IsAuthenticated()]
    
    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        bus = self.get_object()
        serializer = BusLocationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Update bus location
            bus.update_location(
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                speed=serializer.validated_data.get('speed', 0)
            )
            
            # Update fuel level if provided
            if 'fuel_level' in serializer.validated_data:
                bus.fuel_level = serializer.validated_data['fuel_level']
                bus.save()
            
            # Create location history
            LocationHistory.objects.create(
                bus=bus,
                latitude=serializer.validated_data['latitude'],
                longitude=serializer.validated_data['longitude'],
                speed=serializer.validated_data.get('speed', 0),
                accuracy=request.data.get('accuracy')
            )
            
            return Response({
                'success': True,
                'message': 'Location updated',
                'bus': BusSerializer(bus).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def current_trip(self, request, pk=None):
        bus = self.get_object()
        trip = Trip.objects.filter(bus=bus, status='in_progress').first()
        
        if trip:
            from .serializers import TripSerializer
            serializer = TripSerializer(trip)
            return Response(serializer.data)
        
        return Response({
            'message': 'No active trip found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def location_history(self, request, pk=None):
        bus = self.get_object()
        hours = request.query_params.get('hours', 24)
        
        try:
            hours = int(hours)
        except ValueError:
            hours = 24
        
        time_threshold = timezone.now() - timedelta(hours=hours)
        locations = LocationHistory.objects.filter(
            bus=bus,
            timestamp__gte=time_threshold
        ).order_by('-timestamp')
        
        serializer = LocationHistorySerializer(locations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def public_locations(self, request):
        buses = Bus.objects.filter(
            is_tracking_enabled=True,
            status='active'
        ).exclude(
            Q(current_latitude__isnull=True) | Q(current_longitude__isnull=True)
        )
        
        data = []
        for bus in buses:
            data.append({
                'bus_id': bus.id,
                'bus_number': bus.bus_number,
                'latitude': float(bus.current_latitude),
                'longitude': float(bus.current_longitude),
                'speed': bus.current_speed,
                'status': bus.status,
                'driver': bus.driver.user.get_full_name() if hasattr(bus, 'driver') and bus.driver else None,
                'last_updated': bus.last_updated
            })
        
        serializer = PublicBusLocationSerializer(data=data, many=True)
        serializer.is_valid()
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        bus = self.get_object()
        
        # Check permission
        if not (request.user.user_type == 'admin' or 
                (request.user.user_type == 'driver' and 
                 hasattr(request.user, 'driver_profile') and 
                 request.user.driver_profile.assigned_bus == bus)):
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        students = StudentProfile.objects.filter(assigned_bus=bus)
        serializer = StudentProfileSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        bus = self.get_object()
        day = request.query_params.get('day')
        
        schedules = Schedule.objects.filter(bus=bus, is_active=True)
        if day:
            schedules = schedules.filter(day=day)
        
        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

# ==================== Route Views ====================

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.prefetch_related('stops')
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RouteDetailSerializer
        return RouteSerializer
    
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def stops(self, request, pk=None):
        route = self.get_object()
        stops = route.stops.all().order_by('sequence')
        serializer = StopSerializer(stops, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_stop(self, request, pk=None):
        route = self.get_object()
        serializer = StopSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(route=route)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==================== Schedule Views ====================

class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.select_related('bus', 'route')
    serializer_class = ScheduleSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def today(self, request):
        today = datetime.now().strftime('%a').lower()[:3]
        schedules = Schedule.objects.filter(day=today, is_active=True).select_related('bus', 'route')
        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save()
        return Response({
            'success': True,
            'is_active': schedule.is_active
        })

# ==================== Trip Views ====================

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.select_related('bus', 'schedule').prefetch_related('points')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TripCreateSerializer
        return TripSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), CanCreateTrip()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'admin':
            return Trip.objects.all()
        elif user.user_type == 'driver':
            try:
                bus = user.driver_profile.assigned_bus
                return Trip.objects.filter(bus=bus)
            except:
                return Trip.objects.none()
        elif user.user_type == 'student':
            try:
                bus = user.student_profile.assigned_bus
                return Trip.objects.filter(bus=bus)
            except:
                return Trip.objects.none()
        elif user.user_type == 'parent':
            try:
                student = user.parent_profile.student
                return Trip.objects.filter(bus=student.assigned_bus)
            except:
                return Trip.objects.none()
        return Trip.objects.none()
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        trip = self.get_object()
        
        if trip.status != 'scheduled':
            return Response({
                'error': 'Trip cannot be started. Invalid status.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        trip.status = 'in_progress'
        trip.start_time = timezone.now()
        
        # Set start location from bus current location
        if trip.bus.current_latitude and trip.bus.current_longitude:
            trip.start_latitude = trip.bus.current_latitude
            trip.start_longitude = trip.bus.current_longitude
        
        trip.save()
        
        # Notify students
        students = trip.bus.students.all()
        for student in students:
            Notification.objects.create(
                user=student.user,
                notification_type='bus_arrival',
                title=f'Trip Started - Bus {trip.bus.bus_number}',
                message=f'Your bus {trip.bus.bus_number} has started the trip.',
                bus=trip.bus
            )
        
        return Response({
            'success': True,
            'message': 'Trip started',
            'trip': TripSerializer(trip).data
        })
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        trip = self.get_object()
        
        if trip.status != 'in_progress':
            return Response({
                'error': 'Trip is not in progress.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        trip.status = 'completed'
        trip.end_time = timezone.now()
        
        # Set end location from bus current location
        if trip.bus.current_latitude and trip.bus.current_longitude:
            trip.end_latitude = trip.bus.current_latitude
            trip.end_longitude = trip.bus.current_longitude
        
        # Calculate trip metrics
        points = trip.points.all().order_by('timestamp')
        if points.count() > 1:
            # Calculate total distance (simplified)
            trip.total_distance = calculate_trip_distance(points)
            trip.average_speed = points.aggregate(Avg('speed'))['speed__avg'] or 0
        
        trip.save()
        
        return Response({
            'success': True,
            'message': 'Trip ended',
            'trip': TripSerializer(trip).data
        })
    
    @action(detail=True, methods=['post'])
    def add_point(self, request, pk=None):
        trip = self.get_object()
        
        if trip.status != 'in_progress':
            return Response({
                'error': 'Trip is not in progress.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        speed = request.data.get('speed', 0)
        
        if not latitude or not longitude:
            return Response({
                'error': 'Latitude and longitude required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get next sequence number
        sequence = trip.points.count() + 1
        
        point = TripPoint.objects.create(
            trip=trip,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            sequence=sequence,
            timestamp=timezone.now()
        )
        
        serializer = TripPointSerializer(point)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

def calculate_trip_distance(points):
    """Calculate total distance from trip points"""
    from math import radians, sin, cos, sqrt, atan2
    
    total_distance = 0
    
    for i in range(1, len(points)):
        lat1 = float(points[i-1].latitude)
        lon1 = float(points[i-1].longitude)
        lat2 = float(points[i].latitude)
        lon2 = float(points[i].longitude)
        
        # Haversine formula
        R = 6371  # Earth's radius in km
        
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        total_distance += distance
    
    return total_distance

# ==================== Location History Views ====================

class LocationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LocationHistory.objects.select_related('bus')
    serializer_class = LocationHistorySerializer
    
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
    
    def get_permissions(self):
        return [IsAuthenticated()]

# ==================== Notification Views ====================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')
        
        serializer = self.get_serializer(notifications, many=True)
        return Response({
            'count': notifications.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)
        return Response({
            'success': True,
            'message': 'All notifications marked as read'
        })
    
    @action(detail=False, methods=['get'])
    def preferences(self, request):
        prefs, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_preferences(self, request):
        prefs, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Preferences updated',
                'preferences': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==================== Dashboard Views ====================

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if user.user_type == 'admin':
            return self.get_admin_dashboard()
        elif user.user_type == 'driver':
            return self.get_driver_dashboard(user)
        elif user.user_type == 'student':
            return self.get_student_dashboard(user)
        elif user.user_type == 'parent':
            return self.get_parent_dashboard(user)
        
        return Response({
            'error': 'Invalid user type'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_admin_dashboard(self):
        total_buses = Bus.objects.count()
        active_buses = Bus.objects.filter(status='active').count()
        total_students = StudentProfile.objects.count()
        total_drivers = DriverProfile.objects.count()
        total_routes = Route.objects.count()
        active_trips = Trip.objects.filter(status='in_progress').count()
        
        # Recent activities
        recent_locations = LocationHistory.objects.select_related('bus').order_by('-timestamp')[:10]
        recent_notifications = Notification.objects.select_related('user').order_by('-created_at')[:10]
        
        recent_activities = []
        for location in recent_locations:
            recent_activities.append({
                'type': 'location_update',
                'bus': location.bus.bus_number,
                'time': location.timestamp,
                'description': f'Bus {location.bus.bus_number} updated location'
            })
        
        notification_data = NotificationSerializer(recent_notifications, many=True).data
        
        data = {
            'total_buses': total_buses,
            'active_buses': active_buses,
            'total_students': total_students,
            'total_drivers': total_drivers,
            'total_routes': total_routes,
            'active_trips': active_trips,
            'recent_activities': recent_activities,
            'recent_notifications': notification_data
        }
        
        serializer = AdminDashboardSerializer(data)
        return Response(serializer.data)
    
    def get_driver_dashboard(self, user):
        try:
            driver_profile = user.driver_profile
            bus = driver_profile.assigned_bus
            
            if not bus:
                return Response({
                    'error': 'No bus assigned'
                })
            
            # Today's schedule
            today = datetime.now().strftime('%a').lower()[:3]
            schedule = Schedule.objects.filter(bus=bus, day=today, is_active=True).first()
            
            # Current trip
            current_trip = Trip.objects.filter(bus=bus, status='in_progress').first()
            
            # Assigned students
            students = StudentProfile.objects.filter(assigned_bus=bus)[:10]
            
            # Recent locations
            recent_locations = LocationHistory.objects.filter(bus=bus).order_by('-timestamp')[:10]
            
            data = {
                'driver_info': DriverProfileSerializer(driver_profile).data,
                'bus_info': BusSerializer(bus).data,
                'today_schedule': ScheduleSerializer(schedule).data if schedule else None,
                'current_trip': TripSerializer(current_trip).data if current_trip else None,
                'assigned_students': StudentProfileSerializer(students, many=True).data,
                'recent_locations': LocationHistorySerializer(recent_locations, many=True).data
            }
            
            serializer = DriverDashboardSerializer(data)
            return Response(serializer.data)
            
        except DriverProfile.DoesNotExist:
            return Response({
                'error': 'Driver profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def get_student_dashboard(self, user):
        try:
            student_profile = user.student_profile
            bus = student_profile.assigned_bus
            
            if not bus:
                return Response({
                    'error': 'No bus assigned'
                })
            
            # Today's schedule
            today = datetime.now().strftime('%a').lower()[:3]
            schedule = Schedule.objects.filter(bus=bus, day=today, is_active=True).first()
            
            # Bus location
            bus_location = None
            if bus.current_latitude and bus.current_longitude:
                bus_location = {
                    'latitude': float(bus.current_latitude),
                    'longitude': float(bus.current_longitude),
                    'speed': bus.current_speed
                }
            
            # Estimated arrival
            estimated_arrival = None
            if bus_location and student_profile.boarding_stop:
                # Simple estimation
                from math import radians, sin, cos, sqrt, atan2
                
                lat1 = radians(bus_location['latitude'])
                lon1 = radians(bus_location['longitude'])
                lat2 = radians(float(student_profile.boarding_stop.latitude))
                lon2 = radians(float(student_profile.boarding_stop.longitude))
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = 6371 * c  # Distance in km
                
                if bus.current_speed > 0:
                    hours = distance / bus.current_speed
                    estimated_arrival = timezone.now() + timedelta(hours=hours)
            
            # Recent notifications
            notifications = Notification.objects.filter(user=user).order_by('-created_at')[:10]
            
            data = {
                'student_info': StudentProfileSerializer(student_profile).data,
                'bus_info': BusSerializer(bus).data,
                'today_schedule': ScheduleSerializer(schedule).data if schedule else None,
                'bus_location': bus_location,
                'estimated_arrival': estimated_arrival,
                'recent_notifications': NotificationSerializer(notifications, many=True).data
            }
            
            serializer = StudentDashboardSerializer(data)
            return Response(serializer.data)
            
        except StudentProfile.DoesNotExist:
            return Response({
                'error': 'Student profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def get_parent_dashboard(self, user):
        try:
            parent_profile = user.parent_profile
            student = parent_profile.student
            bus = student.assigned_bus
            
            # Bus location
            bus_location = None
            if bus and bus.current_latitude and bus.current_longitude:
                bus_location = {
                    'latitude': float(bus.current_latitude),
                    'longitude': float(bus.current_longitude),
                    'speed': bus.current_speed
                }
            
            # Recent notifications
            notifications = Notification.objects.filter(user=user).order_by('-created_at')[:10]
            
            data = {
                'parent_info': ParentProfileSerializer(parent_profile).data,
                'student_info': StudentProfileSerializer(student).data,
                'bus_info': BusSerializer(bus).data if bus else None,
                'bus_location': bus_location,
                'recent_notifications': NotificationSerializer(notifications, many=True).data
            }
            
            return Response(data)
            
        except ParentProfile.DoesNotExist:
            return Response({
                'error': 'Parent profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

# ==================== Analytics Views ====================

class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        report_type = request.query_params.get('type', 'overview')
        days = int(request.query_params.get('days', 30))
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        if report_type == 'trips':
            return self.get_trip_analytics(start_date, end_date)
        elif report_type == 'buses':
            return self.get_bus_analytics()
        elif report_type == 'students':
            return self.get_student_analytics(start_date, end_date)
        elif report_type == 'drivers':
            return self.get_driver_analytics()
        else:
            return self.get_overview_analytics(start_date, end_date)
    
    def get_overview_analytics(self, start_date, end_date):
        # Trip statistics
        trips = Trip.objects.filter(start_time__date__range=[start_date, end_date])
        total_trips = trips.count()
        completed_trips = trips.filter(status='completed').count()
        cancelled_trips = trips.filter(status='cancelled').count()
        
        # Bus statistics
        total_buses = Bus.objects.count()
        active_buses = Bus.objects.filter(status='active').count()
        
        # Student statistics
        total_students = StudentProfile.objects.count()
        
        # On-time performance
        on_time_trips = trips.filter(status='completed', average_speed__gte=20)  # Simplified
        on_time_rate = (on_time_trips.count() / completed_trips * 100) if completed_trips > 0 else 0
        
        return Response({
            'period': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days
            },
            'trips': {
                'total': total_trips,
                'completed': completed_trips,
                'cancelled': cancelled_trips,
                'on_time_rate': round(on_time_rate, 2)
            },
            'buses': {
                'total': total_buses,
                'active': active_buses,
                'utilization_rate': round(active_buses / total_buses * 100, 2) if total_buses > 0 else 0
            },
            'students': {
                'total': total_students,
                'active': total_students  # Simplified
            }
        })
    
    def get_trip_analytics(self, start_date, end_date):
        trips = Trip.objects.filter(start_time__date__range=[start_date, end_date])
        
        # Group by date
        daily_stats = []
        current_date = start_date
        
        while current_date <= end_date:
            day_trips = trips.filter(start_time__date=current_date)
            daily_stats.append({
                'date': current_date,
                'total_trips': day_trips.count(),
                'completed_trips': day_trips.filter(status='completed').count(),
                'cancelled_trips': day_trips.filter(status='cancelled').count(),
                'total_passengers': day_trips.aggregate(Sum('passenger_count'))['passenger_count__sum'] or 0
            })
            current_date += timedelta(days=1)
        
        return Response({
            'period': {
                'start': start_date,
                'end': end_date,
                'days': (end_date - start_date).days
            },
            'daily_stats': daily_stats,
            'summary': {
                'total_trips': trips.count(),
                'completed_trips': trips.filter(status='completed').count(),
                'cancelled_trips': trips.filter(status='cancelled').count(),
                'total_passengers': trips.aggregate(Sum('passenger_count'))['passenger_count__sum'] or 0,
                'avg_trip_duration': trips.filter(status='completed').aggregate(Avg('end_time - start_time'))['avg']
            }
        })
    
    def get_bus_analytics(self):
        buses = Bus.objects.all()
        bus_data = []
        
        for bus in buses:
            trips = Trip.objects.filter(bus=bus)
            completed_trips = trips.filter(status='completed')
            
            total_distance = completed_trips.aggregate(Sum('total_distance'))['total_distance__sum'] or 0
            avg_speed = completed_trips.aggregate(Avg('average_speed'))['average_speed__avg'] or 0
            total_passengers = trips.aggregate(Sum('passenger_count'))['passenger_count__sum'] or 0
            
            bus_data.append({
                'bus_id': bus.id,
                'bus_number': bus.bus_number,
                'total_trips': trips.count(),
                'total_distance': round(total_distance, 2),
                'average_speed': round(avg_speed, 2),
                'fuel_level': bus.fuel_level,
                'status': bus.status,
                'maintenance_count': bus.maintenance_records.count(),
                'total_passengers': total_passengers
            })
        
        return Response(bus_data)
    
    def get_student_analytics(self, start_date, end_date):
        students = StudentProfile.objects.all()
        student_data = []
        
        for student in students:
            trips = Trip.objects.filter(bus=student.assigned_bus, start_time__date__range=[start_date, end_date])
            
            student_data.append({
                'student_id': student.id,
                'student_name': student.user.get_full_name(),
                'roll_number': student.roll_number,
                'department': student.department,
                'year': student.year,
                'total_trips': trips.count(),
                'bus_number': student.assigned_bus.bus_number if student.assigned_bus else None
            })
        
        return Response(student_data)
    
    def get_driver_analytics(self):
        drivers = DriverProfile.objects.filter(is_active=True)
        driver_data = []
        
        for driver in drivers:
            if driver.assigned_bus:
                trips = Trip.objects.filter(bus=driver.assigned_bus)
                total_trips = trips.count()
                completed_trips = trips.filter(status='completed').count()
                
                driver_data.append({
                    'driver_id': driver.id,
                    'driver_name': driver.user.get_full_name(),
                    'license_number': driver.license_number,
                    'bus_number': driver.assigned_bus.bus_number,
                    'experience': driver.experience,
                    'total_trips': total_trips,
                    'completed_trips': completed_trips,
                    'completion_rate': round(completed_trips / total_trips * 100, 2) if total_trips > 0 else 0
                })
        
        return Response(driver_data)

# ==================== Public Views ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def public_stats(request):
    total_buses = Bus.objects.count()
    active_buses = Bus.objects.filter(status='active').count()
    total_students = StudentProfile.objects.count()
    total_drivers = DriverProfile.objects.count()
    total_routes = Route.objects.count()
    active_trips = Trip.objects.filter(status='in_progress').count()
    
    # Calculate on-time rate (simplified)
    today = timezone.now().date()
    today_trips = Trip.objects.filter(start_time__date=today)
    on_time_trips = today_trips.filter(status='completed', average_speed__gte=20)  # Simplified
    on_time_rate = (on_time_trips.count() / today_trips.count() * 100) if today_trips.count() > 0 else 98
    
    data = {
        'total_buses': total_buses,
        'active_buses': active_buses,
        'total_students': total_students,
        'total_drivers': total_drivers,
        'total_routes': total_routes,
        'active_trips': active_trips,
        'on_time_rate': round(on_time_rate, 2)
    }
    
    serializer = PublicStatsSerializer(data)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def search_buses(request):
    query = request.query_params.get('q', '')
    
    if len(query) < 2:
        return Response([])
    
    buses = Bus.objects.filter(
        Q(bus_number__icontains=query) |
        Q(registration_number__icontains=query) |
        Q(make__icontains=query) |
        Q(model__icontains=query)
    ).select_related('driver')[:10]
    
    results = []
    for bus in buses:
        results.append({
            'id': bus.id,
            'bus_number': bus.bus_number,
            'registration_number': bus.registration_number,
            'status': bus.status,
            'driver': bus.driver.user.get_full_name() if hasattr(bus, 'driver') and bus.driver else None
        })
    
    return Response(results)

@api_view(['GET'])
@permission_classes([AllowAny])
def search_stops(request):
    query = request.query_params.get('q', '')
    
    if len(query) < 2:
        return Response([])
    
    stops = Stop.objects.filter(
        Q(name__icontains=query) |
        Q(route__name__icontains=query)
    ).select_related('route')[:10]
    
    results = []
    for stop in stops:
        results.append({
            'id': stop.id,
            'name': stop.name,
            'route': stop.route.name,
            'latitude': float(stop.latitude),
            'longitude': float(stop.longitude)
        })
    
    return Response(results)

# ==================== Password Reset Views ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset(request):
    serializer = PasswordResetSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generate reset token (simplified - use proper token generation in production)
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Send email (implement with your email settings)
        reset_url = f"{request.build_absolute_uri('/reset-password/')}?uid={uid}&token={token}"
        
        send_mail(
            'Password Reset Request',
            f'Click the following link to reset your password: {reset_url}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        return Response({
            'success': True,
            'message': 'Password reset email sent'
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if serializer.is_valid():
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, serializer.validated_data['token']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Password reset successful'
                })
            else:
                return Response({
                    'error': 'Invalid or expired token'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Invalid reset link'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Add to api/views.py

class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'admin':
            return Issue.objects.all()
        elif user.user_type == 'driver':
            try:
                bus = user.driver_profile.assigned_bus
                return Issue.objects.filter(
                    Q(reported_by=user) | Q(bus=bus)
                ).distinct()
            except:
                return Issue.objects.filter(reported_by=user)
        else:
            return Issue.objects.filter(reported_by=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return IssueCreateSerializer
        return IssueSerializer
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        issue = self.get_object()
        
        # Check permission
        if not (request.user.user_type == 'admin' or 
                (hasattr(request.user, 'driver_profile') and issue.bus == request.user.driver_profile.assigned_bus)):
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        resolution_notes = request.data.get('resolution_notes', '')
        issue.resolve(request.user, resolution_notes)
        
        return Response({
            'success': True,
            'message': 'Issue resolved',
            'issue': IssueSerializer(issue).data
        })
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        issue = self.get_object()
        
        comment_text = request.data.get('comment')
        if not comment_text:
            return Response({
                'error': 'Comment text required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        comment = IssueComment.objects.create(
            issue=issue,
            user=request.user,
            comment=comment_text
        )
        
        serializer = IssueCommentSerializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        issue = self.get_object()
        comments = issue.comments.all()
        serializer = IssueCommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_issues(self, request):
        issues = Issue.objects.filter(reported_by=request.user).order_by('-created_at')
        serializer = self.get_serializer(issues, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get issue statistics"""
        total = Issue.objects.count()
        open_issues = Issue.objects.filter(status='reported').count()
        in_progress = Issue.objects.filter(status='in_progress').count()
        resolved = Issue.objects.filter(status='resolved').count()
        
        by_type = Issue.objects.values('issue_type').annotate(count=Count('id'))
        by_priority = Issue.objects.values('priority').annotate(count=Count('id'))
        
        return Response({
            'total': total,
            'open': open_issues,
            'in_progress': in_progress,
            'resolved': resolved,
            'by_type': by_type,
            'by_priority': by_priority
        })