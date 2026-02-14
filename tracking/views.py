import json
from django.shortcuts import render, get_object_or_404 ,redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import LocationHistory, Trip, TripPoint, GeofenceEvent
from buses.models import Bus, Stop
from accounts.models import StudentProfile
from django.contrib import messages
from buses.models import Bus
from accounts.models import DriverProfile
from tracking.models import Trip  # adjust app name if needed
import math

@login_required
def student_dashboard(request):
    try:
        student_profile = request.user.student_profile
        bus = student_profile.assigned_bus
        
        if not bus:
            return render(request, 'student/dashboard.html', {'error': 'No bus assigned'})
        
        # Get bus location
        bus_location = None
        if bus.current_location:
            bus_location = {
                'latitude': bus.latitude,
                'longitude': bus.longitude,
            }
        
        # Get student's boarding stop
        boarding_stop = student_profile.boarding_stop
        
        # Get estimated arrival time
        estimated_arrival = None
        if boarding_stop and bus_location:
            # Calculate distance and estimated time
            distance = calculate_distance(
                bus_location['latitude'], bus_location['longitude'],
                boarding_stop.latitude, boarding_stop.longitude
            )
            
            if bus.current_speed > 0:
                estimated_minutes = (distance / bus.current_speed) * 60
                estimated_arrival = timezone.now() + timezone.timedelta(minutes=estimated_minutes)
        
        # Get today's schedule
        from datetime import datetime
        today = datetime.now().strftime('%a').lower()[:3]
        schedule = bus.schedules.filter(day=today).first()
        
        context = {
            'student': student_profile,
            'bus': bus,
            'bus_location': bus_location,
            'boarding_stop': boarding_stop,
            'estimated_arrival': estimated_arrival,
            'schedule': schedule,
        }
        
        return render(request, 'student/dashboard.html', context)
    
    except StudentProfile.DoesNotExist:
        return render(request, 'student/dashboard.html', {'error': 'Student profile not found'})

@login_required
def driver_dashboard(request):
    try:
        # Ensure user is a driver
        if request.user.user_type != 'driver':
            return HttpResponse("Unauthorized Access", status=403)

        driver_profile = request.user.driver_profile
        bus = driver_profile.assigned_bus

        active_trip = None
        if bus:
            active_trip = bus.trips.filter(status='in_progress').first()

        context = {
            'driver': driver_profile,
            'bus': bus,
            'active_trip': active_trip
        }

        return render(request, 'driver/dashboard.html', context)

    except DriverProfile.DoesNotExist:
        messages.error(request, "Driver profile not found.")
        return redirect('login')

    except Exception as e:
        print("Driver Dashboard Error:", e)
        return HttpResponse("Internal Server Error", status=500)


@login_required
def track_bus(request, bus_id=None):
    if bus_id:
        bus = get_object_or_404(Bus, id=bus_id)
    else:
        try:
            student_profile = request.user.student_profile
            bus = student_profile.assigned_bus
        except:
            bus = None
    
    if not bus:
        return render(request, 'student/track_bus.html', {'error': 'No bus to track'})
    
    # Get route stops if available
    stops = []
    schedule = bus.schedules.first()
    if schedule and schedule.route:
        stops = schedule.route.stops.all().order_by('sequence')
    
    # Get recent location history
    recent_locations = LocationHistory.objects.filter(bus=bus).order_by('-timestamp')[:10]
    
    context = {
        'bus': bus,
        'stops': stops,
        'recent_locations': recent_locations,
        'google_maps_api_key': 'YOUR_GOOGLE_MAPS_API_KEY',  # Replace with actual key
    }
    
    return render(request, 'student/track_bus.html', context)

@csrf_exempt
@require_POST
def update_location(request, bus_id):
    """API endpoint for drivers to update bus location"""
    try:
        bus = get_object_or_404(Bus, id=bus_id)
        
        # Verify driver owns this bus
        if request.user != bus.driver.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        data = json.loads(request.body)
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        speed = data.get('speed', 0)
        accuracy = data.get('accuracy')
        battery_level = data.get('battery_level')
        
        if not latitude or not longitude:
            return JsonResponse({'error': 'Latitude and longitude required'}, status=400)
        
        # Update bus location
        bus.update_location(latitude, longitude, speed)
        
        # Save to location history
        from django.contrib.gis.geos import Point
        location = Point(longitude, latitude, srid=4326)
        
        LocationHistory.objects.create(
            bus=bus,
            location=location,
            speed=speed,
            accuracy=accuracy,
            battery_level=battery_level
        )
        
        # Check geofences
        check_geofences(bus, location)
        
        # Update active trip if exists
        active_trip = Trip.objects.filter(bus=bus, status='in_progress').first()
        if active_trip:
            TripPoint.objects.create(
                trip=active_trip,
                location=location,
                sequence=TripPoint.objects.filter(trip=active_trip).count() + 1,
                timestamp=timezone.now(),
                speed=speed
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Location updated',
            'bus_number': bus.bus_number,
            'timestamp': timezone.now().isoformat()
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_geofences(bus, location):
    """Check if bus has entered/exited any geofences"""
    from .models import Geofence, GeofenceEvent
    
    # Find all active geofences near the location
    # This is a simplified implementation
    # In production, use proper spatial queries
    geofences = Geofence.objects.filter(is_active=True)
    
    for geofence in geofences:
        # Calculate distance from geofence center
        # Note: This is simplified; actual implementation should use spatial queries
        distance = calculate_distance(
            location.y, location.x,
            geofence.location.centroid.y, geofence.location.centroid.x
        )
        
        if distance <= geofence.radius:
            # Bus is inside geofence
            # Check if this is a new entry
            last_event = GeofenceEvent.objects.filter(
                bus=bus, 
                geofence=geofence
            ).order_by('-timestamp').first()
            
            if not last_event or last_event.event_type != 'inside':
                GeofenceEvent.objects.create(
                    bus=bus,
                    geofence=geofence,
                    event_type='entry',
                    location=location
                )
            
            # Create periodic inside events
            GeofenceEvent.objects.create(
                bus=bus,
                geofence=geofence,
                event_type='inside',
                location=location
            )

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def get_bus_location_history(request, bus_id):
    """Get location history for a specific bus"""
    bus = get_object_or_404(Bus, id=bus_id)
    
    # Check if user has permission to view this bus
    if request.user.user_type == 'student':
        if request.user.student_profile.assigned_bus != bus:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    hours = request.GET.get('hours', 24)
    
    from datetime import timedelta
    time_threshold = timezone.now() - timedelta(hours=int(hours))
    
    locations = LocationHistory.objects.filter(
        bus=bus,
        timestamp__gte=time_threshold
    ).order_by('timestamp').values('latitude', 'longitude', 'speed', 'timestamp')
    
    locations_list = list(locations)
    
    return JsonResponse({
        'bus_number': bus.bus_number,
        'locations': locations_list
    })

@login_required
@require_POST
def start_trip(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)

    if request.user != bus.driver.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    Trip.objects.filter(bus=bus, status='in_progress').update(status='completed')

    trip = Trip.objects.create(
        bus=bus,
        start_time=timezone.now(),
        status='in_progress'
    )

    return JsonResponse({
        'success': True,
        'trip_id': trip.id
    })

@login_required
@require_POST
def stop_trip(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)

    if request.user != bus.driver.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    trip = Trip.objects.filter(bus=bus, status='in_progress').first()

    if not trip:
        return JsonResponse({'error': 'No active trip'}, status=400)

    trip.status = 'completed'
    trip.end_time = timezone.now()
    trip.save()

    return JsonResponse({
        'success': True,
        'message': 'Trip stopped'
    })

@login_required
def get_live_bus_location(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)

    return JsonResponse({
        'bus_number': bus.bus_number,
        'latitude': bus.latitude,
        'longitude': bus.longitude,
        'speed': bus.current_speed
    })