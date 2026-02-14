from django.http import HttpResponse ,JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import update_session_auth_hash,authenticate, login
from .models import User, StudentProfile, DriverProfile
from .forms import UserRegistrationForm, UserLoginForm
from django.contrib.auth.forms import  UserCreationForm
from django.shortcuts import render
from accounts.models import StudentProfile
from django.core.mail import send_mail
from django.utils import timezone
from math import radians, cos, sin, asin, sqrt
from tracking.models import LocationHistory, Trip, TripPoint
import json
from django.conf import settings


def login_view(request):
    # If user is already logged in, redirect based on role
    if request.user.is_authenticated:
        if request.user.user_type == 'admin':
            return redirect('admin_dashboard')
        elif request.user.user_type == 'driver':
            return redirect('driver_dashboard')
        elif request.user.user_type == 'student':
            return redirect('student_dashboard')
        elif request.user.user_type == 'parent':
            return redirect('parent_dashboard')
        else:
            return redirect('home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # Remember me logic (UNCHANGED)
                remember = request.POST.get('remember')
                if remember:
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)

                messages.success(
                    request,
                    f'Welcome back, {user.get_full_name() or user.username}!'
                )

                # ✅ Role-based redirect (THIS IS THE ONLY CHANGE)
                if user.user_type == 'admin':
                    return redirect('admin_dashboard')
                elif user.user_type == 'driver':
                    return redirect('driver_dashboard')
                elif user.user_type == 'student':
                    return redirect('student_dashboard')
                elif user.user_type == 'parent':
                    return redirect('parent_dashboard')
                else:
                    return redirect('home')

            else:
                messages.error(request, 'Invalid username or password.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        print("POST Data:", request.POST)  # Debug: See what's coming in
        
        # Create form with POST data
        form = UserRegistrationForm(request.POST)
        
        if form.is_valid():
            print("Form is valid!")  # Debug
            user = form.save()
            
            # Auto-login after registration
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Smart Bus Tracking.')
            return redirect('dashboard')
        else:
            print("Form errors:", form.errors)  # Debug: See validation errors
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    user = request.user

    try:
        profile = user.student_profile
    except:
        try:
            profile = user.driver_profile
        except:
            profile = None

    context = {
        'profile': profile
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def upload_photo(request):
    if request.method == 'POST' and request.FILES.get('photo'):
        user = request.user
        photo = request.FILES['photo']

        try:
            profile = user.student_profile
        except:
            try:
                profile = user.driver_profile
            except:
                profile = None

        if profile:
            profile.photo = photo
            profile.save()
            messages.success(request, 'Profile photo updated successfully.')

    return redirect('accounts:profile')

@login_required
def update_profile(request):
    user = request.user

    # Ensure the user has a student_profile
    profile, created = StudentProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # Update basic fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.save()

        profile.phone = request.POST.get('phone', profile.phone)
        profile.department = request.POST.get('department', profile.department)
        profile.address = request.POST.get('address', profile.address)
        profile.emergency_name = request.POST.get('emergency_name', profile.emergency_name)
        profile.emergency_phone = request.POST.get('emergency_phone', profile.emergency_phone)

        # Handle profile photo upload
        if request.FILES.get('photo'):
            profile.photo = request.FILES['photo']

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('accounts:profile')  # change to your profile view

    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'accounts/profile_update.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        user = request.user
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('accounts:profile')

        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match.')
            return redirect('accounts:profile')

        user.set_password(new_password1)
        user.save()
        update_session_auth_hash(request, user)

        messages.success(request, 'Password changed successfully.')
        return redirect('accounts:profile')

    return redirect('accounts:profile')

@login_required
def update_notifications(request):
    if request.method == 'POST':
        user = request.user

        email_notifications = request.POST.get('email_notifications') == 'on'
        sms_notifications = request.POST.get('sms_notifications') == 'on'
        push_notifications = request.POST.get('push_notifications') == 'on'

        # assuming notifications are stored on profile
        try:
            profile = user.student_profile
        except:
            try:
                profile = user.driver_profile
            except:
                profile = None

        if profile:
            profile.email_notifications = email_notifications
            profile.sms_notifications = sms_notifications
            profile.push_notifications = push_notifications
            profile.save()

        messages.success(request, 'Notification preferences updated successfully.')

    return redirect('accounts:profile')

@login_required
def student_schedule(request):
    return render(request, 'student/schedule.html')

def admin_dashboard(request):
    return render(request, 'admin/dashboard.html')

def  driver_dashboard(request):
    return render(request, 'driver/dashboard.html')

def student_dashboard(request):
    try:
        student = request.user.student_profile
    except:
        return render(request, "student/dashboard.html", {
            "error": "Student profile not found"
        })

    return render(request, "student/dashboard.html", {
        "student": student
    })

def parent_dashboard(request):
    return render(request, 'parent/dashboard.html')

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km using Haversine formula"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = radians(float(lat1))
    lon1_rad = radians(float(lon1))
    lat2_rad = radians(float(lat2))
    lon2_rad = radians(float(lon2))
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def find_closest_stop(lat, lng, stops):
    """Find the closest stop to current location"""
    closest_stop = None
    min_distance = float('inf')
    
    for stop in stops:
        distance = haversine_distance(lat, lng, stop.latitude, stop.longitude)
        if distance < min_distance:
            min_distance = distance
            closest_stop = stop
    
    # Only consider if within 1 km
    return closest_stop if min_distance <= 1.0 else None

def calculate_eta(current_lat, current_lng, stop_lat, stop_lng, current_speed):
    """Calculate ETA to next stop"""
    distance = haversine_distance(current_lat, current_lng, stop_lat, stop_lng)
    
    # Use current speed or default to 30 km/h
    speed = max(current_speed or 30, 20)  # Minimum 20 km/h
    
    eta_minutes = round((distance / speed) * 60)
    
    if eta_minutes < 1:
        eta = "Arriving now"
    elif eta_minutes < 60:
        eta = f"{eta_minutes} min"
    else:
        hours = eta_minutes // 60
        minutes = eta_minutes % 60
        eta = f"{hours}h {minutes}m"
    
    return {
        'eta': eta,
        'distance': f"{distance:.1f} km"
    }

# ==================== DRIVER DASHBOARD ====================

@login_required
def driver_dashboard(request):
    user = request.user
    context = {'user': user}
    
    try:
        driver_profile = user.driver_profile
        bus = driver_profile.assigned_bus
        
        if bus:
            # Get today's schedule
            today = timezone.now().date()
            schedule = bus.schedules.filter(date=today).first() if hasattr(bus, 'schedules') else None
            
            # Get route stops if schedule exists
            stops = None
            current_stop = None
            next_stop = None
            eta = "--"
            distance = "--"
            
            if schedule and schedule.route:
                stops = schedule.route.stops.all().order_by('sequence')
                
                # Check if there's an active trip using tracking.models.Trip
                active_trip = Trip.objects.filter(
                    bus=bus,
                    status='in_progress'
                ).first()
                
                # Get current location from tracking.models.LocationHistory
                current_location = LocationHistory.objects.filter(bus=bus).first()
                
                # Determine current and next stop based on location
                if current_location and stops:
                    # Find the closest stop to current location
                    closest_stop = find_closest_stop(
                        float(current_location.latitude),
                        float(current_location.longitude),
                        stops
                    )
                    
                    if closest_stop:
                        # Get the index of closest stop
                        stops_list = list(stops)
                        closest_index = stops_list.index(closest_stop)
                        
                        # Current stop is the closest one
                        current_stop = closest_stop
                        
                        # Next stop is the next in sequence if available
                        if closest_index + 1 < len(stops_list):
                            next_stop = stops_list[closest_index + 1]
                            
                            # Calculate ETA to next stop
                            eta_result = calculate_eta(
                                float(current_location.latitude),
                                float(current_location.longitude),
                                float(next_stop.latitude),
                                float(next_stop.longitude),
                                current_location.speed
                            )
                            eta = eta_result['eta']
                            distance = eta_result['distance']
                
                # Check if sharing is active (trip in progress)
                is_sharing = active_trip is not None
                
                context.update({
                    'driver': driver_profile,
                    'bus': bus,
                    'schedule': schedule,
                    'stops': stops,
                    'current_location': current_location,
                    'is_sharing': is_sharing,
                    'current_stop': current_stop,
                    'next_stop': next_stop,
                    'eta': eta,
                    'distance': distance,
                })
            else:
                context.update({
                    'driver': driver_profile,
                    'bus': bus,
                    'error': 'No schedule assigned for today.'
                })
        else:
            context['error'] = 'No bus assigned to you.'
            
    except ObjectDoesNotExist:
        context['error'] = 'Driver profile not found.'
    
    return render(request, 'driver/dashboard.html', context)


# ==================== DRIVER API ENDPOINTS ====================

@login_required
def update_bus_location(request, bus_id):
    """API endpoint to update bus location from driver"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create location history entry using tracking.models.LocationHistory
            location = LocationHistory.objects.create(
                bus_id=bus_id,
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                speed=data.get('speed', 0),
                accuracy=data.get('accuracy', None),
                battery_level=data.get('battery_level', None)
            )
            
            # Get the active trip
            active_trip = Trip.objects.filter(
                bus_id=bus_id,
                status='in_progress'
            ).first()
            
            # If trip is active, record this point
            if active_trip:
                # Get the last point sequence
                last_point = TripPoint.objects.filter(trip=active_trip).order_by('-sequence').first()
                sequence = last_point.sequence + 1 if last_point else 1
                
                # Create trip point
                TripPoint.objects.create(
                    trip=active_trip,
                    latitude=data.get('latitude'),
                    longitude=data.get('longitude'),
                    sequence=sequence,
                    timestamp=timezone.now(),
                    speed=data.get('speed', 0)
                )
                
                # Update trip average speed and distance
                points = TripPoint.objects.filter(trip=active_trip).order_by('sequence')
                if points.count() >= 2:
                    total_distance = 0
                    total_speed = 0
                    
                    for i in range(len(points) - 1):
                        p1 = points[i]
                        p2 = points[i + 1]
                        dist = haversine_distance(
                            float(p1.latitude), float(p1.longitude),
                            float(p2.latitude), float(p2.longitude)
                        )
                        total_distance += dist
                        total_speed += p2.speed
                    
                    active_trip.total_distance = total_distance
                    active_trip.average_speed = total_speed / (points.count() - 1) if points.count() > 1 else 0
                    active_trip.save()
            
            # Get next stop info for response
            from buses.models import Bus, Schedule
            
            bus = Bus.objects.get(id=bus_id)
            today = timezone.now().date()
            schedule = bus.schedules.filter(date=today).first() if hasattr(bus, 'schedules') else None
            
            next_stop_info = None
            eta = "--"
            distance = "--"
            
            if schedule and schedule.route:
                stops = schedule.route.stops.all().order_by('sequence')
                if stops:
                    # Find next stop based on current location
                    closest_stop = find_closest_stop(
                        data.get('latitude'),
                        data.get('longitude'),
                        stops
                    )
                    
                    if closest_stop:
                        stops_list = list(stops)
                        closest_index = stops_list.index(closest_stop)
                        if closest_index + 1 < len(stops_list):
                            next_stop = stops_list[closest_index + 1]
                            eta_result = calculate_eta(
                                data.get('latitude'),
                                data.get('longitude'),
                                float(next_stop.latitude),
                                float(next_stop.longitude),
                                data.get('speed', 0)
                            )
                            next_stop_info = {
                                'name': next_stop.name,
                                'latitude': float(next_stop.latitude),
                                'longitude': float(next_stop.longitude)
                            }
                            eta = eta_result['eta']
                            distance = eta_result['distance']
            
            return JsonResponse({
                'success': True,
                'message': 'Location updated successfully',
                'next_stop': next_stop_info,
                'eta': eta,
                'distance': distance,
                'timestamp': location.timestamp.isoformat()
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def start_trip(request, bus_id):
    """API endpoint to start a trip"""
    if request.method == 'POST':
        try:
            # Check if there's already an active trip
            active_trip = Trip.objects.filter(
                bus_id=bus_id,
                status='in_progress'
            ).first()
            
            if active_trip:
                return JsonResponse({
                    'success': False,
                    'error': 'A trip is already in progress'
                }, status=400)
            
            # Get current location
            current_location = LocationHistory.objects.filter(bus_id=bus_id).first()
            
            # Create new trip using tracking.models.Trip
            trip = Trip.objects.create(
                bus_id=bus_id,
                driver=request.user.driver_profile,
                start_time=timezone.now(),
                status='in_progress',
                start_latitude=current_location.latitude if current_location else None,
                start_longitude=current_location.longitude if current_location else None
            )
            
            return JsonResponse({
                'success': True,
                'trip_id': trip.id,
                'message': 'Trip started successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def end_trip(request, bus_id):
    """API endpoint to end a trip"""
    if request.method == 'POST':
        try:
            trip = Trip.objects.filter(
                bus_id=bus_id,
                status='in_progress'
            ).last()
            
            if trip:
                # Get final location
                current_location = LocationHistory.objects.filter(bus_id=bus_id).first()
                
                trip.end_time = timezone.now()
                trip.status = 'completed'
                trip.end_latitude = current_location.latitude if current_location else None
                trip.end_longitude = current_location.longitude if current_location else None
                trip.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Trip ended successfully',
                    'trip_id': trip.id,
                    'total_distance': trip.total_distance,
                    'average_speed': trip.average_speed
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No active trip found'
                }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def passenger_list(request, bus_id):
    """View to show passenger list"""
    from .models import StudentProfile
    
    passengers = StudentProfile.objects.filter(
        assigned_bus_id=bus_id,
        is_active=True
    ).select_related('user')
    
    context = {
        'passengers': passengers,
        'bus_id': bus_id
    }
    return render(request, 'driver/passengers.html', context)

@login_required
def contact_admin(request):
    """View for drivers to contact administrator"""
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        issue_type = request.POST.get('issue_type')
        
        # Get user info
        user = request.user
        user_type = user.get_user_type_display()
        
        # Prepare email content
        email_subject = f"[{issue_type}] {subject} - {user.get_full_name()} ({user_type})"
        
        email_message = f"""
        Message from: {user.get_full_name()}
        Username: {user.username}
        User Type: {user_type}
        Email: {user.email}
        Phone: {user.phone_number}
        
        Issue Type: {issue_type}
        
        Message:
        {message}
        
        ---
        This is an automated message from the Smart College Bus Tracking System.
        """
        
        try:
            # Send email to admin
            send_mail(
                email_subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],  # Make sure this is set in settings.py
                fail_silently=False,
            )
            
            # Also save to database if you want to track issues
            if hasattr(request.user, 'driver_profile'):
                from .models import Issue
                Issue.objects.create(
                    bus=request.user.driver_profile.assigned_bus,
                    reported_by=request.user,
                    description=f"{issue_type}: {subject}\n\n{message}",
                    status='reported'
                )
            
            messages.success(request, 'Your message has been sent to the administrator. They will contact you soon.')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Error sending message: {str(e)}')
            return redirect('contact_admin')
    
    # Get driver's bus info for context
    bus_info = None
    if hasattr(request.user, 'driver_profile') and request.user.driver_profile.assigned_bus:
        bus = request.user.driver_profile.assigned_bus
        bus_info = {
            'bus_number': bus.bus_number,
            'bus_type': bus.get_bus_type_display(),
            'status': bus.get_status_display()
        }
    
    context = {
        'bus_info': bus_info
    }
    return render(request, 'driver/contact_admin.html', context)

@login_required
def my_issues(request):
    """View for drivers to see their reported issues"""
    
    if hasattr(request.user, 'driver_profile'):
        from .models import Issue
        issues = Issue.objects.filter(reported_by=request.user).order_by('-created_at')
        
        context = {
            'issues': issues
        }
        return render(request, 'driver/my_issues.html', context)
    
    return redirect('dashboard')

@login_required
def dashboard_view(request):
    """
    Main dashboard view that handles different user types
    """
    user = request.user
    context = {
        'user': user,
        'now': timezone.now(),
    }

    # ADMIN DASHBOARD
    if user.user_type == 'admin':
        # Get statistics for admin dashboard
        total_buses = Bus.objects.count()
        active_buses = Bus.objects.filter(status='active').count()
        total_drivers = DriverProfile.objects.filter(is_active=True).count()
        total_students = StudentProfile.objects.filter(is_active=True).count()
        active_trips = Trip.objects.filter(status='in_progress').count()
        recent_issues = Issue.objects.filter(status='reported').order_by('-created_at')[:5]
        
        context.update({
            'total_buses': total_buses,
            'active_buses': active_buses,
            'total_drivers': total_drivers,
            'total_students': total_students,
            'active_trips': active_trips,
            'recent_issues': recent_issues,
        })
        return render(request, 'admin/dashboard.html', context)

    # DRIVER DASHBOARD
    elif user.user_type == 'driver':
        try:
            # Get driver profile
            driver_profile = user.driver_profile
            
            # Get assigned bus
            bus = driver_profile.assigned_bus
            
            if bus:
                # Get today's schedule
                today = timezone.now().date()
                schedule = Schedule.objects.filter(
                    bus=bus,
                    date=today
                ).first()
                
                # Get route stops if schedule exists
                stops = None
                current_stop = None
                next_stop = None
                
                if schedule and schedule.route:
                    stops = schedule.route.stops.all().order_by('sequence')
                    
                    # Determine current and next stop
                    if stops.exists():
                        # Get last reported location to determine current stop
                        last_location = BusLocation.objects.filter(bus=bus).last()
                        
                        if last_location:
                            # Find nearest stop
                            from math import radians, cos, sin, asin, sqrt
                            def haversine(lat1, lon1, lat2, lon2):
                                R = 6371  # Earth's radius in km
                                lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                                dlat = lat2 - lat1
                                dlon = lon2 - lon1
                                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                                c = 2 * asin(sqrt(a))
                                return R * c
                            
                            min_distance = float('inf')
                            for stop in stops:
                                distance = haversine(
                                    last_location.latitude, last_location.longitude,
                                    stop.latitude, stop.longitude
                                )
                                if distance < min_distance:
                                    min_distance = distance
                                    current_stop = stop
                            
                            # Find next stop
                            if current_stop:
                                next_stops = stops.filter(sequence__gt=current_stop.sequence)
                                if next_stops.exists():
                                    next_stop = next_stops.first()
                                else:
                                    # Loop back to first stop if at end
                                    next_stop = stops.first()
                        else:
                            # No location yet, first stop is current
                            current_stop = stops.first()
                            next_stop = stops.filter(sequence__gt=current_stop.sequence).first()
                
                # Get current location
                current_location = BusLocation.objects.filter(bus=bus).last()
                
                # Calculate ETA to next stop
                eta = "Calculating..."
                distance_to_next = "N/A"
                
                if current_location and next_stop:
                    from math import radians, cos, sin, asin, sqrt
                    def haversine(lat1, lon1, lat2, lon2):
                        R = 6371
                        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                        dlat = lat2 - lat1
                        dlon = lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        c = 2 * asin(sqrt(a))
                        return R * c
                    
                    distance = haversine(
                        current_location.latitude, current_location.longitude,
                        next_stop.latitude, next_stop.longitude
                    )
                    
                    distance_to_next = f"{distance:.1f} km"
                    
                    # Assume average speed 30 km/h for ETA
                    avg_speed = 30  # km/h
                    eta_minutes = int((distance / avg_speed) * 60)
                    if eta_minutes < 1:
                        eta = "Less than 1 min"
                    elif eta_minutes < 60:
                        eta = f"{eta_minutes} min"
                    else:
                        eta = f"{eta_minutes // 60}h {eta_minutes % 60}m"
                
                # Check if trip is active (location sharing on)
                is_sharing = Trip.objects.filter(
                    bus=bus,
                    status='in_progress',
                    end_time__isnull=True
                ).exists()
                
                context.update({
                    'driver': driver_profile,
                    'bus': bus,
                    'schedule': schedule,
                    'stops': stops,
                    'current_stop': current_stop,
                    'next_stop': next_stop,
                    'current_location': current_location,
                    'is_sharing': is_sharing,
                    'eta': eta,
                    'distance': distance_to_next,
                })
            else:
                context['error'] = 'No bus assigned to you.'
                
        except ObjectDoesNotExist:
            context['error'] = 'Driver profile not found.'
        
        return render(request, 'driver/dashboard.html', context)

    # STUDENT AND PARENT DASHBOARD (SHARED)
    elif user.user_type == 'student' or user.user_type == 'parent':
        try:
            # For student
            if user.user_type == 'student':
                profile = user.student_profile
            # For parent - assuming parent has access to student's info
            else:
                # You might need to adjust this based on your parent model
                # For now, get the first child or handle appropriately
                profile = StudentProfile.objects.filter(
                    parent=user  # Assuming parent field exists
                ).first()
            
            if profile and profile.assigned_bus:
                bus = profile.assigned_bus
                
                # Get bus current location
                current_location = BusLocation.objects.filter(bus=bus).last()
                
                # Get today's schedule
                today = timezone.now().date()
                schedule = Schedule.objects.filter(
                    bus=bus,
                    date=today
                ).first()
                
                # Get route stops
                stops = None
                if schedule and schedule.route:
                    stops = schedule.route.stops.all().order_by('sequence')
                
                # Calculate ETA to next stop
                eta = "Not available"
                if current_location and stops:
                    # Find next stop based on bus position
                    # This is simplified - you might want more sophisticated logic
                    next_stop = stops.first()
                    
                    # Calculate ETA logic here
                    # ... (similar to driver calculation)
                    
                context.update({
                    'profile': profile,
                    'bus': bus,
                    'bus_location': current_location,
                    'schedule': schedule,
                    'stops': stops,
                    'eta': eta,
                    'user_type': user.user_type,
                })
            else:
                context['error'] = 'No bus assigned to you.'
                
        except ObjectDoesNotExist:
            context['error'] = 'Profile not found.'
        
        return render(request, 'student/dashboard.html', context)

    # DEFAULT FALLBACK
    return render(request, 'dashboard.html', context)

@login_required
def report_issue(request):
    """API endpoint to report issues"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get bus if driver
            bus = None
            if request.user.user_type == 'driver' and hasattr(request.user, 'driver_profile'):
                bus = request.user.driver_profile.assigned_bus
            
            issue = Issue.objects.create(
                bus=bus,
                reported_by=request.user,
                description=data.get('issue', ''),
                status='reported'
            )
            
            # Send email to admin
            try:
                subject = f"New Issue Reported - {request.user.get_full_name()}"
                message = f"""
                Issue ID: {issue.id}
                Reported By: {request.user.get_full_name()} ({request.user.user_type})
                Email: {request.user.email}
                Bus: {bus.bus_number if bus else 'N/A'}
                
                Description:
                {data.get('issue', '')}
                
                Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL],
                    fail_silently=True,
                )
            except:
                pass  # Email fails silently
            
            return JsonResponse({
                'success': True,
                'issue_id': issue.id,
                'message': 'Issue reported successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)