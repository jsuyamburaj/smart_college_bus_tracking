from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'admin'

class IsDriverUser(permissions.BasePermission):
    """
    Custom permission to only allow driver users to access.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'driver'

class IsStudentUser(permissions.BasePermission):
    """
    Custom permission to only allow student users to access.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'student'

class IsParentUser(permissions.BasePermission):
    """
    Custom permission to only allow parent users to access.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'parent'

class IsProfileOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Check if user is admin
        if request.user.user_type == 'admin':
            return True
        
        # Check if user is owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'student'):
            return obj.student.user == request.user
        
        return False

class IsAssignedDriver(permissions.BasePermission):
    """
    Custom permission to check if user is the assigned driver for a bus.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.user_type != 'driver':
            return False
        
        try:
            driver_profile = request.user.driver_profile
            return driver_profile.assigned_bus == obj
        except:
            return False

class IsAssignedStudent(permissions.BasePermission):
    """
    Custom permission to check if user is assigned to a specific bus.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.user_type != 'student':
            return False
        
        try:
            student_profile = request.user.student_profile
            return student_profile.assigned_bus == obj
        except:
            return False

class CanTrackBus(permissions.BasePermission):
    """
    Permission to check if user can track a bus.
    Students can track their assigned bus, admins can track all.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.user_type == 'admin':
            return True
        
        if user.user_type == 'student':
            try:
                return user.student_profile.assigned_bus == obj
            except:
                return False
        
        if user.user_type == 'parent':
            try:
                parent_profile = user.parent_profile
                return parent_profile.student.assigned_bus == obj
            except:
                return False
        
        return False

class HasBusAssignment(permissions.BasePermission):
    """
    Permission to check if user has a bus assignment.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if user.user_type == 'driver':
            try:
                return user.driver_profile.assigned_bus is not None
            except:
                return False
        
        if user.user_type == 'student':
            try:
                return user.student_profile.assigned_bus is not None
            except:
                return False
        
        return True

class IsVerifiedUser(permissions.BasePermission):
    """
    Permission to check if user is verified.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has a `user` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must have an attribute named `user`.
        return obj.user == request.user

class UserTypePermission(permissions.BasePermission):
    """
    Permission based on user type with custom actions.
    """
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated:
            return False
        
        # Map user types to allowed methods
        permissions_map = {
            'admin': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'driver': ['GET', 'PUT', 'PATCH'],
            'student': ['GET', 'PUT', 'PATCH'],
            'parent': ['GET'],
        }
        
        allowed_methods = permissions_map.get(user.user_type, [])
        return request.method in allowed_methods

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