from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import os

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create corresponding profile when a user is created.
    """
    if created:
        if instance.user_type == 'student':
            from .models import StudentProfile
            StudentProfile.objects.create(user=instance)
        elif instance.user_type == 'driver':
            from .models import DriverProfile
            DriverProfile.objects.create(user=instance)
        elif instance.user_type == 'parent':
            from .models import ParentProfile
            ParentProfile.objects.create(user=instance)
        
        # Send welcome email
        send_welcome_email(instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the corresponding profile when a user is saved.
    """
    try:
        if instance.user_type == 'student':
            instance.student_profile.save()
        elif instance.user_type == 'driver':
            instance.driver_profile.save()
        elif instance.user_type == 'parent':
            instance.parent_profile.save()
    except:
        # Profile might not exist yet
        pass

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Send welcome email to new users.
    """
    if created and instance.email:
        try:
            subject = f'Welcome to Smart College Bus Tracking System'
            message = render_to_string('accounts/emails/welcome_email.html', {
                'user': instance,
                'site_name': 'Smart Bus Tracking',
            })
            
            send_mail(
                subject,
                '',  # Plain text version (empty since we're using HTML)
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                html_message=message,
                fail_silently=True,
            )
        except Exception as e:
            # Log error but don't crash
            print(f"Error sending welcome email: {e}")

@receiver(pre_save, sender=User)
def generate_username(sender, instance, **kwargs):
    """
    Generate username from email if not provided.
    """
    if not instance.username and instance.email:
        # Use email prefix as username
        instance.username = instance.email.split('@')[0]
        
        # Ensure uniqueness
        original_username = instance.username
        counter = 1
        while User.objects.filter(username=instance.username).exclude(pk=instance.pk).exists():
            instance.username = f"{original_username}{counter}"
            counter += 1

@receiver(post_save, sender='accounts.StudentProfile')
def generate_student_qr_code(sender, instance, created, **kwargs):
    """
    Generate QR code for student when profile is created or updated.
    """
    if instance.roll_number:
        # Generate QR code data
        qr_data = f"""
        Student ID: {instance.id}
        Roll No: {instance.roll_number}
        Name: {instance.user.get_full_name()}
        Department: {instance.department}
        Year: {instance.year}
        Bus: {instance.assigned_bus.bus_number if instance.assigned_bus else 'Not Assigned'}
        Emergency: {instance.emergency_contact}
        """
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to Django File
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        
        # Generate filename
        filename = f'qr_code_{instance.roll_number}.png'
        
        # Delete old QR code if exists
        if instance.qr_code:
            old_file_path = instance.qr_code.path
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Save new QR code
        instance.qr_code.save(filename, File(buffer), save=False)
        instance.save()

@receiver(post_save, sender='accounts.StudentProfile')
def notify_parent_on_bus_assignment(sender, instance, **kwargs):
    """
    Notify parents when their child is assigned to a bus.
    """
    # Check if bus assignment changed
    if instance.assigned_bus:
        try:
            # Get all parents of this student
            parents = instance.parents.all()
            
            for parent in parents:
                try:
                    subject = f'Bus Assignment Updated for {instance.user.get_full_name()}'
                    message = render_to_string('accounts/emails/bus_assignment_email.html', {
                        'student': instance,
                        'parent': parent,
                        'bus': instance.assigned_bus,
                    })
                    
                    send_mail(
                        subject,
                        '',
                        settings.DEFAULT_FROM_EMAIL,
                        [parent.user.email],
                        html_message=message,
                        fail_silently=True,
                    )
                except:
                    pass
        except:
            pass

@receiver(post_save, sender='accounts.DriverProfile')
def notify_driver_on_bus_assignment(sender, instance, **kwargs):
    """
    Notify driver when assigned to a bus.
    """
    if instance.assigned_bus and instance.user.email:
        try:
            subject = f'You have been assigned to Bus {instance.assigned_bus.bus_number}'
            message = render_to_string('accounts/emails/driver_assignment_email.html', {
                'driver': instance,
                'bus': instance.assigned_bus,
            })
            
            send_mail(
                subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [instance.user.email],
                html_message=message,
                fail_silently=True,
            )
        except:
            pass

@receiver(post_save, sender='accounts.DriverProfile')
def update_driver_status(sender, instance, **kwargs):
    """
    Update driver's active status based on license expiry.
    """
    from datetime import date
    
    if instance.license_expiry and instance.license_expiry < date.today():
        instance.is_active = False
        # Don't save here to avoid recursion, will be saved by caller

@receiver(pre_save, sender=User)
def deactivate_unverified_users(sender, instance, **kwargs):
    """
    Deactivate users who haven't been verified after certain period.
    """
    from datetime import timedelta
    from django.utils import timezone
    
    # Check if user is not verified and created more than 7 days ago
    if not instance.is_verified and instance.created_at:
        days_since_creation = (timezone.now() - instance.created_at).days
        if days_since_creation > 7:
            instance.is_active = False

@receiver(post_save, sender='accounts.ParentProfile')
def send_parent_invitation(sender, instance, created, **kwargs):
    """
    Send invitation email to parent when profile is created.
    """
    if created and instance.user.email:
        try:
            subject = f'Invitation to Track {instance.student.user.get_full_name()}'
            message = render_to_string('accounts/emails/parent_invitation_email.html', {
                'parent': instance,
                'student': instance.student,
            })
            
            send_mail(
                subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [instance.user.email],
                html_message=message,
                fail_silently=True,
            )
        except:
            pass

# Additional signal handlers for bus tracking
@receiver(post_save, sender='tracking.LocationHistory')
def check_bus_speed_limit(sender, instance, **kwargs):
    """
    Check if bus is exceeding speed limit and notify if necessary.
    """
    SPEED_LIMIT = 80  # km/h
    
    if instance.speed > SPEED_LIMIT:
        # Get bus driver
        bus = instance.bus
        if bus.driver:
            try:
                subject = f'Speed Limit Warning - Bus {bus.bus_number}'
                message = render_to_string('accounts/emails/speed_warning_email.html', {
                    'bus': bus,
                    'driver': bus.driver.user.get_full_name(),
                    'speed': instance.speed,
                    'limit': SPEED_LIMIT,
                    'location': f"{instance.latitude}, {instance.longitude}",
                    'timestamp': instance.timestamp,
                })
                
                send_mail(
                    subject,
                    '',
                    settings.DEFAULT_FROM_EMAIL,
                    [bus.driver.user.email],
                    html_message=message,
                    fail_silently=True,
                )
                
                # Also notify admin
                admin_users = User.objects.filter(user_type='admin', is_active=True)
                for admin in admin_users:
                    if admin.email:
                        send_mail(
                            f'Speed Alert: Bus {bus.bus_number}',
                            '',
                            settings.DEFAULT_FROM_EMAIL,
                            [admin.email],
                            html_message=message,
                            fail_silently=True,
                        )
            except:
                pass

@receiver(post_save, sender='buses.BusMaintenance')
def notify_bus_maintenance(sender, instance, created, **kwargs):
    """
    Notify driver about bus maintenance.
    """
    if created and instance.bus.driver:
        try:
            subject = f'Maintenance Scheduled for Bus {instance.bus.bus_number}'
            message = render_to_string('accounts/emails/maintenance_notification_email.html', {
                'maintenance': instance,
                'bus': instance.bus,
                'driver': instance.bus.driver.user.get_full_name(),
            })
            
            send_mail(
                subject,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [instance.bus.driver.user.email],
                html_message=message,
                fail_silently=True,
            )
        except:
            pass