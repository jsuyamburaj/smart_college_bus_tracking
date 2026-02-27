from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('driver', 'Driver'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"


class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    roll_number = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100)
    year = models.IntegerField(null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    address = models.TextField()
    
    phone = models.CharField(max_length=15, null=True, blank=True)  # <-- added
    emergency_name = models.CharField(max_length=100, null=True, blank=True)  # <-- added
    emergency_contact = models.CharField(max_length=15, null=True, blank=True)  # <-- added
    created_at = models.DateTimeField(auto_now_add=True)  # <-- added
    assigned_bus = models.ForeignKey(
        'buses.Bus',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    boarding_stop = models.ForeignKey(
        'buses.Stop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.roll_number}"


class DriverProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='driver_profile'
    )
    license_number = models.CharField(max_length=50, unique=True)
    experience = models.IntegerField(help_text="Years of experience")
    address = models.TextField()
    emergency_contact = models.CharField(max_length=15)
    assigned_bus = models.OneToOneField(
        'buses.Bus',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver'
    )
    is_active = models.BooleanField(default=True)
    license_expiry = models.DateField()

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.license_number}"


class ParentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='parents'
    )
    relationship = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.user.get_full_name()} - Parent of {self.student.user.get_full_name()}"