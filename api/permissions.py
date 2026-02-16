from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == 'admin'

class IsDriverUser(permissions.BasePermission):
    """
    Custom permission to only allow driver users to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == 'driver'

class IsStudentUser(permissions.BasePermission):
    """
    Custom permission to only allow student users to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == 'student'

class IsParentUser(permissions.BasePermission):
    """
    Custom permission to only allow parent users to access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.user_type == 'parent'

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if the object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'student') and hasattr(obj.student, 'user'):
            return obj.student.user == request.user
        
        return False

class IsAssignedDriver(permissions.BasePermission):
    """
    Permission to check if user is the assigned driver for a bus.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or request.user.user_type != 'driver':
            return False
        
        try:
            driver_profile = request.user.driver_profile
            # If obj is a bus
            if hasattr(obj, 'driver'):
                return obj.driver == driver_profile
            # If obj has a bus attribute
            elif hasattr(obj, 'bus') and hasattr(obj.bus, 'driver'):
                return obj.bus.driver == driver_profile
        except:
            pass
        
        return False

class IsAssignedStudent(permissions.BasePermission):
    """
    Permission to check if user is the assigned student for a bus.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or request.user.user_type != 'student':
            return False
        
        try:
            student_profile = request.user.student_profile
            # If obj is a bus
            if hasattr(obj, 'students'):
                return student_profile in obj.students.all()
            # If obj has a bus attribute
            elif hasattr(obj, 'bus'):
                return student_profile.assigned_bus == obj.bus
        except:
            pass
        
        return False

class CanAccessBusLocation(permissions.BasePermission):
    """
    Permission to check if user can access bus location.
    Admins: all buses
    Drivers: their assigned bus
    Students: their assigned bus
    Parents: their child's bus
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        # Admin can access all
        if user.user_type == 'admin':
            return True
        
        # Driver - their assigned bus
        if user.user_type == 'driver':
            try:
                return obj == user.driver_profile.assigned_bus
            except:
                return False
        
        # Student - their assigned bus
        if user.user_type == 'student':
            try:
                return obj == user.student_profile.assigned_bus
            except:
                return False
        
        # Parent - their child's bus
        if user.user_type == 'parent':
            try:
                return obj == user.parent_profile.student.assigned_bus
            except:
                return False
        
        return False

class IsVerifiedUser(permissions.BasePermission):
    """
    Permission to check if user is verified.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified

class HasBusAssignment(permissions.BasePermission):
    """
    Permission to check if user has a bus assignment.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type == 'driver':
            try:
                return request.user.driver_profile.assigned_bus is not None
            except:
                return False
        
        if request.user.user_type == 'student':
            try:
                return request.user.student_profile.assigned_bus is not None
            except:
                return False
        
        return False

class CanCreateTrip(permissions.BasePermission):
    """
    Permission to check if user can create a trip.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin can create trips
        if request.user.user_type == 'admin':
            return True
        
        # Driver can create trips for their bus
        if request.user.user_type == 'driver':
            try:
                bus = request.user.driver_profile.assigned_bus
                return bus is not None
            except:
                return False
        
        return False

class CanUpdateLocation(permissions.BasePermission):
    """
    Permission to check if user can update bus location.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Only drivers can update location
        if request.user.user_type != 'driver':
            return False
        
        # Check if driver has an assigned bus
        try:
            return request.user.driver_profile.assigned_bus is not None
        except:
            return False
    
    def has_object_permission(self, request, view, obj):
        # Check if driver is updating their own bus
        try:
            return obj == request.user.driver_profile.assigned_bus
        except:
            return False

class CanViewReports(permissions.BasePermission):
    """
    Permission to check if user can view reports.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin can view all reports
        if request.user.user_type == 'admin':
            return True
        
        # Drivers can view their own trip reports
        if request.user.user_type == 'driver':
            return True
        
        return False

# Composite permissions
class IsAdminOrDriver(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ['admin', 'driver']

class IsAdminOrStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ['admin', 'student']

class IsAdminOrParent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ['admin', 'parent']

class IsStudentOrParent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ['student', 'parent']