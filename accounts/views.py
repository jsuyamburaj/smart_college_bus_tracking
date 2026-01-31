from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, StudentProfile, DriverProfile
from .forms import UserRegistrationForm, UserLoginForm, ProfileUpdateForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                
                # Redirect based on user type
                if user.user_type == 'admin':
                    return redirect('admin_dashboard')
                elif user.user_type == 'driver':
                    return redirect('driver_dashboard')
                elif user.user_type == 'student':
                    return redirect('student_dashboard')


                elif user.user_type == 'parent':
                    return redirect('parent_dashboard')
                else:
                    return redirect('dashboard')
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
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Create profile based on user type
            if user.user_type == 'student':
                StudentProfile.objects.create(
                    user=user,
                    roll_number=form.cleaned_data.get('roll_number'),
                    department=form.cleaned_data.get('department'),
                    year=form.cleaned_data.get('year')
                )
            elif user.user_type == 'driver':
                DriverProfile.objects.create(
                    user=user,
                    license_number=form.cleaned_data.get('license_number'),
                    experience=form.cleaned_data.get('experience')
                )
            
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Smart Bus Tracking.')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_view(request):
    user = request.user
    profile = None
    
    if user.user_type == 'student':
        profile = user.student_profile
    elif user.user_type == 'driver':
        profile = user.driver_profile
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=user)
    
    context = {
        'form': form,
        'profile': profile
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def dashboard_view(request):
    user = request.user
    context = {'user': user}
    
    if user.user_type == 'admin':
        return render(request, 'admin/dashboard.html', context)
    elif user.user_type == 'driver':
        # Get driver's bus and schedule
        try:
            driver_profile = user.driver_profile
            bus = driver_profile.assigned_bus
            context['bus'] = bus
            context['schedule'] = bus.schedules.first() if bus else None
        except:
            pass
        return render(request, 'driver/dashboard.html', context)
    elif user.user_type == 'student':
        # Get student's bus and location
        try:
            student_profile = user.student_profile
            bus = student_profile.assigned_bus
            context['bus'] = bus
            if bus and bus.current_location:
                context['bus_location'] = bus.current_location
        except:
            pass
        return render(request, 'student/dashboard.html', context)
    elif user.user_type == 'parent':
        return render(request, 'parent/dashboard.html', context)
    
    return render(request, 'dashboard.html', context)