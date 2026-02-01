# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, StudentProfile, DriverProfile, ParentProfile
import re
from django.contrib.auth.forms import AuthenticationForm

class UserRegistrationForm(UserCreationForm):
    """Custom registration form that matches your HTML"""
    
    # Add fields from your HTML form
    user_type = forms.ChoiceField(
        choices=[
            ('student', 'Student'),
            ('parent', 'Parent'),
            ('driver', 'Driver'),
            ('admin', 'Administrator'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Personal Information
    phone = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1 (555) 123-4567'
        })
    )
    
    # Student specific fields
    roll_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    year = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    # Driver specific fields
    license_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    experience = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    # Terms agreement
    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = [
            'user_type', 'first_name', 'last_name', 'email', 'phone',
            'username', 'password1', 'password2',
            'roll_number', 'department', 'year',  # Student fields
            'license_number', 'experience',  # Driver fields
            'terms'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        """Custom validation based on user type"""
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        
        # Validate based on user type
        if user_type == 'student':
            if not cleaned_data.get('roll_number'):
                self.add_error('roll_number', 'Roll number is required for students.')
            if not cleaned_data.get('department'):
                self.add_error('department', 'Department is required for students.')
            if not cleaned_data.get('year'):
                self.add_error('year', 'Year is required for students.')
        
        elif user_type == 'driver':
            if not cleaned_data.get('license_number'):
                self.add_error('license_number', 'License number is required for drivers.')
            if not cleaned_data.get('experience'):
                self.add_error('experience', 'Experience is required for drivers.')
        
        # Validate phone number
        phone = cleaned_data.get('phone')
        if phone:
            # Remove non-digit characters
            phone_digits = re.sub(r'\D', '', phone)
            if len(phone_digits) < 10:
                self.add_error('phone', 'Please enter a valid phone number.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save user and create appropriate profile"""
        user = super().save(commit=False)
        user.user_type = self.cleaned_data['user_type']
        user.phone = self.cleaned_data['phone']
        
        if commit:
            user.save()
            
            # Create appropriate profile
            if user.user_type == 'student':
                StudentProfile.objects.create(
                    user=user,
                    roll_number=self.cleaned_data.get('roll_number', ''),
                    department=self.cleaned_data.get('department', ''),
                    year=self.cleaned_data.get('year', 1)
                )
            elif user.user_type == 'driver':
                DriverProfile.objects.create(
                    user=user,
                    license_number=self.cleaned_data.get('license_number', ''),
                    experience=self.cleaned_data.get('experience', 0)
                )
            elif user.user_type == 'parent':
                ParentProfile.objects.create(
                    user=user
                )
        
        return user

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'id': 'username'
        }),
        label='Username or Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password'
        }),
        label='Password'
    )
    remember = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'remember'
        }),
        label='Remember me'
    )