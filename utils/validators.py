import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime, date

def validate_phone_number(value):
    """
    Validate phone number format.
    """
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', value)
    
    # Check if it's a valid phone number (10-15 digits)
    if not (10 <= len(phone) <= 15):
        raise ValidationError(
            _('Phone number must have between 10 and 15 digits.'),
            params={'value': value},
        )
    
    return phone

def validate_email(value):
    """
    Validate email format.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Enter a valid email address.'),
            params={'value': value},
        )
    return value

def validate_username(value):
    """
    Validate username format.
    """
    pattern = r'^[a-zA-Z0-9_.-]+$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Username can only contain letters, numbers, dots, underscores and hyphens.'),
            params={'value': value},
        )
    
    if len(value) < 3:
        raise ValidationError(
            _('Username must be at least 3 characters long.'),
            params={'value': value},
        )
    
    if len(value) > 150:
        raise ValidationError(
            _('Username cannot exceed 150 characters.'),
            params={'value': value},
        )
    
    return value

def validate_password_strength(value):
    """
    Validate password strength.
    """
    if len(value) < 8:
        raise ValidationError(
            _('Password must be at least 8 characters long.'),
            params={'value': value},
        )
    
    if not re.search(r'[A-Z]', value):
        raise ValidationError(
            _('Password must contain at least one uppercase letter.'),
            params={'value': value},
        )
    
    if not re.search(r'[a-z]', value):
        raise ValidationError(
            _('Password must contain at least one lowercase letter.'),
            params={'value': value},
        )
    
    if not re.search(r'\d', value):
        raise ValidationError(
            _('Password must contain at least one number.'),
            params={'value': value},
        )
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise ValidationError(
            _('Password must contain at least one special character.'),
            params={'value': value},
        )
    
    return value

def validate_license_plate(value):
    """
    Validate license plate format (simplified).
    """
    pattern = r'^[A-Z0-9-]+$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('License plate can only contain uppercase letters, numbers, and hyphens.'),
            params={'value': value},
        )
    
    if len(value) < 5 or len(value) > 15:
        raise ValidationError(
            _('License plate must be between 5 and 15 characters.'),
            params={'value': value},
        )
    
    return value

def validate_latitude(value):
    """
    Validate latitude value.
    """
    try:
        lat = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            _('Latitude must be a number.'),
            params={'value': value},
        )
    
    if lat < -90 or lat > 90:
        raise ValidationError(
            _('Latitude must be between -90 and 90.'),
            params={'value': value},
        )
    
    return lat

def validate_longitude(value):
    """
    Validate longitude value.
    """
    try:
        lng = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            _('Longitude must be a number.'),
            params={'value': value},
        )
    
    if lng < -180 or lng > 180:
        raise ValidationError(
            _('Longitude must be between -180 and 180.'),
            params={'value': value},
        )
    
    return lng

def validate_speed(value):
    """
    Validate speed value.
    """
    try:
        speed = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            _('Speed must be a number.'),
            params={'value': value},
        )
    
    if speed < 0 or speed > 200:
        raise ValidationError(
            _('Speed must be between 0 and 200 km/h.'),
            params={'value': value},
        )
    
    return speed

def validate_fuel_level(value):
    """
    Validate fuel level percentage.
    """
    try:
        fuel = float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            _('Fuel level must be a number.'),
            params={'value': value},
        )
    
    if fuel < 0 or fuel > 100:
        raise ValidationError(
            _('Fuel level must be between 0 and 100.'),
            params={'value': value},
        )
    
    return fuel

def validate_year(value):
    """
    Validate year value.
    """
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise ValidationError(
            _('Year must be a number.'),
            params={'value': value},
        )
    
    current_year = datetime.now().year
    if year < 1900 or year > current_year + 1:
        raise ValidationError(
            _(f'Year must be between 1900 and {current_year + 1}.'),
            params={'value': value},
        )
    
    return year

def validate_date(value):
    """
    Validate date format.
    """
    if isinstance(value, date):
        return value
    
    try:
        if isinstance(value, str):
            return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError(
            _('Date must be in YYYY-MM-DD format.'),
            params={'value': value},
        )
    
    return value

def validate_time(value):
    """
    Validate time format.
    """
    if isinstance(value, str):
        try:
            # Try HH:MM format
            return datetime.strptime(value, '%H:%M').time()
        except ValueError:
            try:
                # Try HH:MM:SS format
                return datetime.strptime(value, '%H:%M:%S').time()
            except ValueError:
                raise ValidationError(
                    _('Time must be in HH:MM or HH:MM:SS format.'),
                    params={'value': value},
                )
    
    return value

def validate_positive_integer(value):
    """
    Validate positive integer.
    """
    try:
        num = int(value)
    except (TypeError, ValueError):
        raise ValidationError(
            _('Value must be an integer.'),
            params={'value': value},
        )
    
    if num < 0:
        raise ValidationError(
            _('Value must be positive.'),
            params={'value': value},
        )
    
    return num

def validate_file_extension(value, allowed_extensions):
    """
    Validate file extension.
    """
    import os
    ext = os.path.splitext(value.name)[1][1:].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            _(f'File extension must be one of: {", ".join(allowed_extensions)}'),
            params={'value': value},
        )
    
    return value

def validate_file_size(value, max_size_mb=5):
    """
    Validate file size.
    """
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            _(f'File size must not exceed {max_size_mb} MB.'),
            params={'value': value},
        )
    
    return value

def validate_image_file(value):
    """
    Validate image file.
    """
    import imghdr
    from django.core.files.images import get_image_dimensions
    
    # Check extension
    allowed = ['jpg', 'jpeg', 'png', 'gif', 'bmp']
    validate_file_extension(value, allowed)
    
    # Check file size (5MB max)
    validate_file_size(value, 5)
    
    # Check if it's actually an image
    try:
        w, h = get_image_dimensions(value)
        if w is None or h is None:
            raise ValidationError(
                _('Invalid image file.'),
                params={'value': value},
            )
        
        # Check minimum dimensions
        if w < 100 or h < 100:
            raise ValidationError(
                _('Image dimensions must be at least 100x100 pixels.'),
                params={'value': value},
            )
        
        # Check maximum dimensions
        if w > 4096 or h > 4096:
            raise ValidationError(
                _('Image dimensions must not exceed 4096x4096 pixels.'),
                params={'value': value},
            )
        
    except Exception as e:
        raise ValidationError(
            _(f'Invalid image file: {str(e)}'),
            params={'value': value},
        )
    
    return value

def validate_json(value):
    """
    Validate JSON string.
    """
    import json
    
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValidationError(
                _(f'Invalid JSON: {str(e)}'),
                params={'value': value},
            )
    
    return value

def validate_color_hex(value):
    """
    Validate hex color code.
    """
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Color must be a valid hex code (e.g., #FF0000).'),
            params={'value': value},
        )
    
    return value

def validate_bus_number(value):
    """
    Validate bus number format.
    """
    pattern = r'^[A-Z0-9-]+$'
    if not re.match(pattern, value):
        raise ValidationError(
            _('Bus number can only contain uppercase letters, numbers, and hyphens.'),
            params={'value': value},
        )
    
    if len(value) < 3 or len(value) > 20:
        raise ValidationError(
            _('Bus number must be between 3 and 20 characters.'),
            params={'value': value},
        )
    
    return value

def validate_route_name(value):
    """
    Validate route name.
    """
    if len(value) < 3 or len(value) > 100:
        raise ValidationError(
            _('Route name must be between 3 and 100 characters.'),
            params={'value': value},
        )
    
    return value

def validate_stop_name(value):
    """
    Validate stop name.
    """
    if len(value) < 2 or len(value) > 100:
        raise ValidationError(
            _('Stop name must be between 2 and 100 characters.'),
            params={'value': value},
        )
    
    return value