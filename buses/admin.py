from django.contrib import admin
from .models import Bus, Route, Stop, Schedule, BusMaintenance

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_number', 'registration_number', 'bus_type', 'capacity', 'status', 'driver_name')
    list_filter = ('bus_type', 'status', 'is_tracking_enabled')
    search_fields = ('bus_number', 'registration_number', 'make', 'model')
    readonly_fields = ('last_updated', 'created_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('bus_number', 'registration_number', 'bus_type', 'capacity')
        }),
        ('Location & Status', {
            'fields': ('current_latitude', 'current_longitude', 'current_speed', 'fuel_level', 'status', 'is_tracking_enabled')
        }),
        ('Bus Details', {
            'fields': ('make', 'model', 'year', 'color', 'insurance_expiry', 'permit_expiry')
        }),
        ('Timestamps', {
            'fields': ('last_updated', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def driver_name(self, obj):
        if obj.driver:
            return obj.driver.user.get_full_name()
        return "Not assigned"
    driver_name.short_description = 'Driver'

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_distance', 'estimated_duration', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)

@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('name', 'route', 'sequence', 'latitude', 'longitude', 'estimated_arrival_time')
    list_filter = ('route', 'is_pickup_point', 'is_drop_point')
    search_fields = ('name', 'route__name')
    list_editable = ('sequence',)
    
    fieldsets = (
        ('Stop Information', {
            'fields': ('name', 'route', 'sequence')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Schedule & Type', {
            'fields': ('estimated_arrival_time', 'is_pickup_point', 'is_drop_point')
        }),
    )

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('bus', 'route', 'day', 'departure_time', 'arrival_time', 'is_active')
    list_filter = ('day', 'is_active', 'bus')
    search_fields = ('bus__bus_number', 'route__name')
    list_editable = ('is_active',)

# FIXED VERSION - Remove readonly_fields or add created_at to model
@admin.register(BusMaintenance)
class BusMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('bus', 'maintenance_date', 'maintenance_type', 'cost', 'next_maintenance_date', 'performed_by')
    list_filter = ('maintenance_type', 'maintenance_date')
    search_fields = ('bus__bus_number', 'maintenance_type', 'performed_by', 'description')
    # readonly_fields = ('created_at',)  # REMOVED OR COMMENTED OUT
    date_hierarchy = 'maintenance_date'
    
    fieldsets = (
        ('Maintenance Details', {
            'fields': ('bus', 'maintenance_date', 'maintenance_type', 'description', 'cost')
        }),
        ('Future Planning', {
            'fields': ('next_maintenance_date', 'performed_by')
        }),
    )