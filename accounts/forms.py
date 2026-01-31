# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, StudentProfile, DriverProfile, ParentProfile
import re

class UserRegistrationForm(UserCreationForm):
    """Custom registration form with user type"""
    
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('driver', 'Driver'),
        ('parent', 'Parent'),
    ]
    
    # Additional fields for different user types
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES, 
        widget=forms.RadioSelect,
        required=True,
        initial='student'
    )
    
    # Student specific fields
    roll_number = forms.CharField(
        max_length=20, 
        required=False,
        label='Roll Number',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your roll number'})
    )
    
    department = forms.CharField(
        max_length=100, 
        required=False,
        label='Department',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Computer Science'})
    )
    
    year = forms.IntegerField(
        required=False,
        label='Year',
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g., 3'})
    )
    
    # Driver specific fields
    license_number = forms.CharField(
        max_length=50, 
        required=False,
        label='License Number',
        widget=forms.TextInput(attrs={'placeholder': 'Enter driving license number'})
    )
    
    experience = forms.IntegerField(
        required=False,
        label='Experience (years)',
        min_value=0,
        max_value=50,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g., 5'})
    )
    
    # Parent specific fields
    phone = forms.CharField(
        max_length=15, 
        required=False,
        label='Phone Number',
        widget=forms.TextInput(attrs={'placeholder': '+91 9876543210'})
    )
    
    address = forms.CharField(
        required=False,
        label='Address',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter your address'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'placeholder': 'your.email@example.com'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter last name'}),
        }
    
    def clean(self):
        """Custom validation for different user types"""
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        
        # Student validation
        if user_type == 'student':
            roll_number = cleaned_data.get('roll_number')
            department = cleaned_data.get('department')
            year = cleaned_data.get('year')
            
            if not roll_number:
                self.add_error('roll_number', 'Roll number is required for students.')
            if not department:
                self.add_error('department', 'Department is required for students.')
            if not year:
                self.add_error('year', 'Year is required for students.')
            elif year < 1 or year > 5:
                self.add_error('year', 'Year must be between 1 and 5.')
        
        # Driver validation
        elif user_type == 'driver':
            license_number = cleaned_data.get('license_number')
            experience = cleaned_data.get('experience')
            
            if not license_number:
                self.add_error('license_number', 'License number is required for drivers.')
            if experience is None:
                self.add_error('experience', 'Experience is required for drivers.')
            elif experience < 0:
                self.add_error('experience', 'Experience cannot be negative.')
        
        # Parent validation
        elif user_type == 'parent':
            phone = cleaned_data.get('phone')
            
            if not phone:
                self.add_error('phone', 'Phone number is required for parents.')
            elif not re.match(r'^\+?1?\d{9,15}$', phone):
                self.add_error('phone', 'Enter a valid phone number.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save user and create appropriate profile"""
        user = super().save(commit=False)
        user_type = self.cleaned_data.get('user_type')
        
        if commit:
            user.save()
            
            # Create appropriate profile
            if user_type == 'student':
                StudentProfile.objects.create(
                    user=user,
                    roll_number=self.cleaned_data.get('roll_number'),
                    department=self.cleaned_data.get('department'),
                    year=self.cleaned_data.get('year')
                )
            elif user_type == 'driver':
                DriverProfile.objects.create(
                    user=user,
                    license_number=self.cleaned_data.get('license_number'),
                    experience=self.cleaned_data.get('experience')
                )
            elif user_type == 'parent':
                ParentProfile.objects.create(
                    user=user,
                    phone=self.cleaned_data.get('phone'),
                    address=self.cleaned_data.get('address')
                )
        
        return user

class UserLoginForm(AuthenticationForm):
    """Custom login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

class ProfileUpdateForm(forms.ModelForm):
    """Profile update form"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']