import math
import requests
from django.conf import settings

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth using the haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate the bearing between two points.
    Returns bearing in degrees (0-360).
    """
    dlon = math.radians(lon2 - lon1)
    
    x = math.sin(dlon) * math.cos(math.radians(lat2))
    y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    
    bearing = math.degrees(math.atan2(x, y))
    bearing = (bearing + 360) % 360
    
    return bearing

def calculate_midpoint(lat1, lon1, lat2, lon2):
    """
    Calculate the midpoint between two points.
    """
    dlon = math.radians(lon2 - lon1)
    
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    lon1 = math.radians(lon1)
    
    Bx = math.cos(lat2) * math.cos(dlon)
    By = math.cos(lat2) * math.sin(dlon)
    
    lat3 = math.atan2(math.sin(lat1) + math.sin(lat2),
                      math.sqrt((math.cos(lat1) + Bx)**2 + By**2))
    lon3 = lon1 + math.atan2(By, math.cos(lat1) + Bx)
    
    return (math.degrees(lat3), math.degrees(lon3))

def is_point_in_polygon(point, polygon):
    """
    Check if a point is inside a polygon using ray casting algorithm.
    point: (lat, lon)
    polygon: list of (lat, lon) points
    """
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def get_address_from_coordinates(lat, lon):
    """
    Get address from coordinates using reverse geocoding.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        return None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'latlng': f"{lat},{lon}",
        'key': settings.GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            return data['results'][0]['formatted_address']
    except:
        pass
    
    return None

def get_coordinates_from_address(address):
    """
    Get coordinates from address using geocoding.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        return None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': address,
        'key': settings.GOOGLE_MAPS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return (location['lat'], location['lng'])
    except:
        pass
    
    return None

def calculate_route_distance(points):
    """
    Calculate total distance of a route from a list of points.
    points: list of (lat, lon) tuples
    """
    total_distance = 0
    
    for i in range(1, len(points)):
        lat1, lon1 = points[i-1]
        lat2, lon2 = points[i]
        total_distance += haversine_distance(lat1, lon1, lat2, lon2)
    
    return total_distance

def find_nearest_point(target_lat, target_lon, points):
    """
    Find the nearest point in a list to the target.
    points: list of (lat, lon) tuples
    Returns: index of nearest point and distance
    """
    min_distance = float('inf')
    nearest_index = -1
    
    for i, (lat, lon) in enumerate(points):
        distance = haversine_distance(target_lat, target_lon, lat, lon)
        if distance < min_distance:
            min_distance = distance
            nearest_index = i
    
    return nearest_index, min_distance

def is_speed_excessive(speed_kmh, speed_limit=80):
    """
    Check if speed is excessive.
    """
    return speed_kmh > speed_limit

def is_within_geofence(center_lat, center_lon, radius_km, point_lat, point_lon):
    """
    Check if a point is within a circular geofence.
    """
    distance = haversine_distance(center_lat, center_lon, point_lat, point_lon)
    return distance <= radius_km

def calculate_estimated_arrival(current_lat, current_lon, dest_lat, dest_lon, speed_kmh):
    """
    Calculate estimated arrival time.
    """
    distance = haversine_distance(current_lat, current_lon, dest_lat, dest_lon)
    
    if speed_kmh <= 0:
        return None
    
    hours = distance / speed_kmh
    minutes = hours * 60
    
    from datetime import datetime, timedelta
    return datetime.now() + timedelta(minutes=minutes)

def calculate_average_speed(points_with_time):
    """
    Calculate average speed from points with timestamps.
    points_with_time: list of (lat, lon, timestamp) tuples
    """
    if len(points_with_time) < 2:
        return 0
    
    total_distance = 0
    total_time = 0
    
    for i in range(1, len(points_with_time)):
        lat1, lon1, t1 = points_with_time[i-1]
        lat2, lon2, t2 = points_with_time[i]
        
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        time_diff = (t2 - t1).total_seconds() / 3600  # hours
        
        total_distance += distance
        total_time += time_diff
    
    if total_time == 0:
        return 0
    
    return total_distance / total_time

def generate_route_polyline(points):
    """
    Generate Google Maps polyline encoded string from points.
    """
    from googlemaps.converter import encode_polyline
    
    # Convert to format expected by googlemaps
    route_points = [(lat, lon) for lat, lon in points]
    return encode_polyline(route_points)

def decode_polyline(polyline_str):
    """
    Decode Google Maps polyline string to list of points.
    """
    from googlemaps.converter import decode_polyline
    
    decoded = decode_polyline(polyline_str)
    return [(point['lat'], point['lng']) for point in decoded]