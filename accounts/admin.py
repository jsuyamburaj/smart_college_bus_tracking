from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, StudentProfile, DriverProfile, ParentProfile

class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'
    fields = ('roll_number', 'department', 'year', 'semester', 'address', 
              'emergency_contact', 'assigned_bus', 'boarding_stop', 'qr_code')
    # Remove autocomplete_fields
    raw_id_fields = ('assigned_bus', 'boarding_stop')  # Use raw_id_fields instead

class DriverProfileInline(admin.StackedInline):
    model = DriverProfile
    can_delete = False
    verbose_name_plural = 'Driver Profile'
    fk_name = 'user'
    fields = ('license_number', 'experience', 'address', 'emergency_contact',
              'assigned_bus', 'is_active', 'license_expiry')
    # Remove autocomplete_fields
    raw_id_fields = ('assigned_bus',)  # Use raw_id_fields instead

class ParentProfileInline(admin.StackedInline):
    model = ParentProfile
    can_delete = False
    verbose_name_plural = 'Parent Profile'
    fk_name = 'user'
    fields = ('student', 'relationship')
    # Remove autocomplete_fields
    raw_id_fields = ('student',)  # Use raw_id_fields instead

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'phone', 'user_type', 'first_name', 
                    'last_name', 'is_staff', 'is_active', 'is_verified')
    list_filter = ('user_type', 'is_staff', 'is_active', 'is_verified', 'created_at')
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name', 'email', 
                                        'phone', 'profile_image', 'user_type')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 
                                      'is_verified', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'user_type', 'password1', 'password2'),
        }),
    )
    
    def get_inlines(self, request, obj=None):
        if obj:
            if obj.user_type == 'student':
                return [StudentProfileInline]
            elif obj.user_type == 'driver':
                return [DriverProfileInline]
            elif obj.user_type == 'parent':
                return [ParentProfileInline]
        return []

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'get_user', 'department', 'year', 'semester', 
                    'get_bus', 'get_boarding_stop')
    list_filter = ('department', 'year', 'semester')
    search_fields = ('roll_number', 'user__username', 'user__email', 
                     'user__first_name', 'user__last_name')
    # Remove autocomplete_fields and use raw_id_fields
    raw_id_fields = ('user', 'assigned_bus', 'boarding_stop')
    
    fieldsets = (
        (_('Student Info'), {
            'fields': ('user', 'roll_number', 'department', 'year', 'semester')
        }),
        (_('Contact Info'), {
            'fields': ('address', 'emergency_contact')
        }),
        (_('Bus Assignment'), {
            'fields': ('assigned_bus', 'boarding_stop', 'qr_code')
        }),
    )
    
    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'Username'
    get_user.admin_order_field = 'user__username'
    
    def get_bus(self, obj):
        return obj.assigned_bus.bus_number if obj.assigned_bus else None
    get_bus.short_description = 'Bus'
    get_bus.admin_order_field = 'assigned_bus__bus_number'
    
    def get_boarding_stop(self, obj):
        return obj.boarding_stop.name if obj.boarding_stop else None
    get_boarding_stop.short_description = 'Boarding Stop'
    get_boarding_stop.admin_order_field = 'boarding_stop__name'

@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('license_number', 'get_user', 'experience', 'get_bus', 
                    'is_active', 'license_expiry')
    list_filter = ('is_active', 'license_expiry', 'experience')
    search_fields = ('license_number', 'user__username', 'user__email', 
                     'user__first_name', 'user__last_name')
    # Remove autocomplete_fields and use raw_id_fields
    raw_id_fields = ('user', 'assigned_bus')
    
    fieldsets = (
        (_('Driver Info'), {
            'fields': ('user', 'license_number', 'experience', 'license_expiry')
        }),
        (_('Contact Info'), {
            'fields': ('address', 'emergency_contact')
        }),
        (_('Assignment'), {
            'fields': ('assigned_bus', 'is_active')
        }),
    )
    
    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'Username'
    get_user.admin_order_field = 'user__username'
    
    def get_bus(self, obj):
        return obj.assigned_bus.bus_number if obj.assigned_bus else None
    get_bus.short_description = 'Bus'
    get_bus.admin_order_field = 'assigned_bus__bus_number'

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('get_user', 'get_student', 'relationship')
    list_filter = ('relationship',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 
                     'user__last_name', 'student__user__first_name', 
                     'student__user__last_name')
    # Remove autocomplete_fields and use raw_id_fields
    raw_id_fields = ('user', 'student')
    
    fieldsets = (
        (_('Parent Info'), {
            'fields': ('user', 'student', 'relationship')
        }),
    )
    
    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'Parent Username'
    get_user.admin_order_field = 'user__username'
    
    def get_student(self, obj):
        return f"{obj.student.user.get_full_name()} ({obj.student.roll_number})"
    get_student.short_description = 'Student'
    get_student.admin_order_field = 'student__user__first_name'