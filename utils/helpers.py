import re
import random
import string
import hashlib
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

def generate_random_string(length=10):
    """Generate a random string of fixed length."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def generate_qr_data(user_id, user_type, timestamp=None):
    """Generate QR code data for user identification."""
    if timestamp is None:
        timestamp = timezone.now()
    
    data = {
        'user_id': user_id,
        'user_type': user_type,
        'timestamp': timestamp.isoformat(),
        'random': generate_random_string(8)
    }
    
    # Add hash for security
    data_string = f"{user_id}{user_type}{timestamp}{data['random']}{settings.SECRET_KEY}"
    data['hash'] = hashlib.sha256(data_string.encode()).hexdigest()[:16]
    
    return json.dumps(data)

def verify_qr_data(qr_data):
    """Verify QR code data."""
    try:
        data = json.loads(qr_data)
        
        # Check required fields
        required = ['user_id', 'user_type', 'timestamp', 'random', 'hash']
        if not all(field in data for field in required):
            return None
        
        # Verify hash
        data_string = f"{data['user_id']}{data['user_type']}{data['timestamp']}{data['random']}{settings.SECRET_KEY}"
        expected_hash = hashlib.sha256(data_string.encode()).hexdigest()[:16]
        
        if data['hash'] != expected_hash:
            return None
        
        # Check timestamp (not older than 24 hours)
        timestamp = datetime.fromisoformat(data['timestamp'])
        if timezone.now() - timestamp > timedelta(hours=24):
            return None
        
        return {
            'user_id': data['user_id'],
            'user_type': data['user_type']
        }
    except:
        return None

def format_phone_number(phone):
    """Format phone number to international format."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Handle different formats
    if len(digits) == 10:
        return f"+1{digits}"  # Assuming US/Canada
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) > 11:
        return f"+{digits}"
    else:
        return phone

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_user_agent(request):
    """Get user agent from request."""
    return request.META.get('HTTP_USER_AGENT', '')

def is_mobile_device(request):
    """Check if request is from mobile device."""
    user_agent = get_user_agent(request).lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)

def paginate_queryset(queryset, page=1, page_size=20):
    """Paginate a queryset."""
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        'items': queryset[start:end],
        'total': queryset.count(),
        'page': page,
        'page_size': page_size,
        'pages': (queryset.count() + page_size - 1) // page_size
    }

def send_email_template(subject, template_name, context, to_emails, from_email=None):
    """Send email using template."""
    from django.template.loader import render_to_string
    
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    html_message = render_to_string(f'emails/{template_name}.html', context)
    text_message = render_to_string(f'emails/{template_name}.txt', context)
    
    send_mail(
        subject=subject,
        message=text_message,
        from_email=from_email,
        recipient_list=to_emails,
        html_message=html_message,
        fail_silently=False,
    )

def get_time_slots(interval_minutes=30):
    """Generate time slots for scheduling."""
    slots = []
    start = datetime.strptime('00:00', '%H:%M')
    end = datetime.strptime('23:59', '%H:%M')
    
    current = start
    while current <= end:
        slots.append(current.strftime('%H:%M'))
        current += timedelta(minutes=interval_minutes)
    
    return slots

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula.
    Returns distance in kilometers.
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def calculate_eta(current_lat, current_lon, dest_lat, dest_lon, speed_kmh):
    """
    Calculate estimated time of arrival in minutes.
    """
    distance = calculate_distance(current_lat, current_lon, dest_lat, dest_lon)
    
    if speed_kmh <= 0:
        return None
    
    hours = distance / speed_kmh
    minutes = hours * 60
    
    return round(minutes, 1)

def format_duration(minutes):
    """Format minutes into human-readable duration."""
    if minutes < 1:
        return "Less than a minute"
    elif minutes < 60:
        return f"{int(minutes)} minute{'s' if minutes > 1 else ''}"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if mins == 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            return f"{hours}h {mins}m"

def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def truncate_text(text, length=100, suffix="..."):
    """Truncate text to specified length."""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix

def camel_to_snake(name):
    """Convert CamelCase to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def snake_to_camel(name):
    """Convert snake_case to CamelCase."""
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def dict_to_camel_case(data):
    """Convert dictionary keys from snake_case to camelCase."""
    if isinstance(data, dict):
        return {snake_to_camel(k): dict_to_camel_case(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [dict_to_camel_case(item) for item in data]
    else:
        return data

def dict_to_snake_case(data):
    """Convert dictionary keys from camelCase to snake_case."""
    if isinstance(data, dict):
        return {camel_to_snake(k): dict_to_snake_case(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [dict_to_snake_case(item) for item in data]
    else:
        return data