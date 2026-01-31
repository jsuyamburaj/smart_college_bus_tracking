from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Count, Q
from .models import Bus, Route, Stop, Schedule
from accounts.models import StudentProfile, DriverProfile
from tracking.models import LocationHistory
import json

def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

def is_driver(user):
    return user.is_authenticated and user.user_type == 'driver'

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_buses = Bus.objects.count()
    active_buses = Bus.objects.filter(status='active').count()
    total_routes = Route.objects.count()
    total_students = StudentProfile.objects.count()
    total_drivers = DriverProfile.objects.count()
    
    # Get buses with current locations
    buses_with_locations = Bus.objects.filter(current_location__isnull=False)
    
    # Get recent activities
    recent_locations = LocationHistory.objects.select_related('bus').order_by('-timestamp')[:10]
    
    context = {
        'total_buses': total_buses,
        'active_buses': active_buses,
        'total_routes': total_routes,
        'total_students': total_students,
        'total_drivers': total_drivers,
        'buses': buses_with_locations,
        'recent_locations': recent_locations,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def bus_list(request):
    buses = Bus.objects.all().order_by('-created_at')
    return render(request, 'admin/buses/list.html', {'buses': buses})

@login_required
@user_passes_test(is_admin)
def bus_detail(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    students = StudentProfile.objects.filter(assigned_bus=bus)
    schedule = Schedule.objects.filter(bus=bus).first()
    maintenance_records = bus.maintenance_records.all().order_by('-maintenance_date')
    
    # Get location history
    location_history = LocationHistory.objects.filter(bus=bus).order_by('-timestamp')[:50]
    
    context = {
        'bus': bus,
        'students': students,
        'schedule': schedule,
        'maintenance_records': maintenance_records,
        'location_history': location_history,
    }
    
    return render(request, 'admin/buses/detail.html', context)

@login_required
@user_passes_test(is_admin)
def add_bus(request):
    if request.method == 'POST':
        # Process form data
        bus_data = {
            'bus_number': request.POST.get('bus_number'),
            'registration_number': request.POST.get('registration_number'),
            'bus_type': request.POST.get('bus_type'),
            'capacity': request.POST.get('capacity'),
            'make': request.POST.get('make'),
            'model': request.POST.get('model'),
            'year': request.POST.get('year'),
            'color': request.POST.get('color'),
        }
        
        bus = Bus.objects.create(**bus_data)
        return redirect('bus_detail', bus_id=bus.id)
    
    return render(request, 'admin/buses/create.html')

@login_required
@user_passes_test(is_admin)
def route_list(request):
    routes = Route.objects.all().prefetch_related('stops')
    return render(request, 'admin/routes/list.html', {'routes': routes})

@login_required
@user_passes_test(is_driver)
def driver_dashboard(request):
    try:
        driver_profile = request.user.driver_profile
        bus = driver_profile.assigned_bus
        
        if not bus:
            return render(request, 'driver/dashboard.html', {'error': 'No bus assigned'})
        
        # Get today's schedule
        from datetime import datetime
        today = datetime.now().strftime('%a').lower()[:3]
        schedule = Schedule.objects.filter(bus=bus, day=today).first()
        
        # Get route stops
        stops = []
        if schedule and schedule.route:
            stops = schedule.route.stops.all().order_by('sequence')
        
        # Get current location
        current_location = None
        if bus.current_location:
            current_location = {
                'latitude': bus.latitude,
                'longitude': bus.longitude,
            }
        
        context = {
            'bus': bus,
            'schedule': schedule,
            'stops': stops,
            'current_location': current_location,
            'driver': driver_profile,
        }
        
        return render(request, 'driver/dashboard.html', context)
    
    except DriverProfile.DoesNotExist:
        return render(request, 'driver/dashboard.html', {'error': 'Driver profile not found'})

def get_bus_locations(request):
    """API endpoint to get all bus locations for map display"""
    buses = Bus.objects.filter(
        current_location__isnull=False,
        is_tracking_enabled=True
    ).values(
        'id', 'bus_number', 'latitude', 'longitude', 
        'current_speed', 'status', 'driver__user__first_name',
        'driver__user__last_name'
    )
    
    locations = []
    for bus in buses:
        if bus['latitude'] and bus['longitude']:
            locations.append({
                'bus_id': bus['id'],
                'bus_number': bus['bus_number'],
                'latitude': bus['latitude'],
                'longitude': bus['longitude'],
                'speed': bus['current_speed'],
                'status': bus['status'],
                'driver_name': f"{bus['driver__user__first_name']} {bus['driver__user__last_name']}",
                'popup_content': f"""
                    <strong>{bus['bus_number']}</strong><br>
                    Status: {bus['status']}<br>
                    Speed: {bus['current_speed']} km/h<br>
                    Driver: {bus['driver__user__first_name']} {bus['driver__user__last_name']}
                """
            })
    
    return JsonResponse({'locations': locations})