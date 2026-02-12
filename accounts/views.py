from django.http import HttpResponse
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


def login_view(request):
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')  # Redirect to the dashboard URL name
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        
        if form.is_valid():
            # Get username and password from form
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Login user
                login(request, user)
                
                # Set session expiry based on "remember me"
                remember = request.POST.get('remember')
                if remember:
                    # Set session to expire in 2 weeks
                    request.session.set_expiry(1209600)  # 2 weeks in seconds
                else:
                    # Set session to expire when browser closes
                    request.session.set_expiry(0)
                
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # ✅ FIX: Redirect to the main dashboard view which handles user types
                return redirect('dashboard')
                
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            # Form has errors
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
def dashboard_view(request):
    user = request.user
    context = {'user': user}

    if user.user_type == 'admin':
        return render(request, 'admin/dashboard.html', context)

    elif user.user_type == 'driver':
        try:
            driver_profile = user.driver_profile
            bus = driver_profile.assigned_bus
            context['bus'] = bus
            context['schedule'] = bus.schedules.first() if bus else None
        except ObjectDoesNotExist:
            pass
        return render(request, 'driver/dashboard.html', context)

    elif user.user_type == 'student':
        try:
            student_profile = user.student_profile
            bus = student_profile.assigned_bus
            context['bus'] = bus
            if bus and getattr(bus, 'current_location', None):
                context['bus_location'] = bus.current_location
        except ObjectDoesNotExist:
            pass
        return render(request, 'student/dashboard.html', context)

    elif user.user_type == 'parent':
        return render(request, 'parent/dashboard.html', context)

    return render(request, 'dashboard.html', context)

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
