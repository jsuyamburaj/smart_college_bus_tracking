from django.contrib import admin
from .models import LocationHistory, Geofence, GeofenceEvent, Trip, TripPoint

@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ('bus', 'latitude', 'longitude', 'speed', 'timestamp')
    list_filter = ('bus', 'timestamp')
    search_fields = ('bus__bus_number',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Location Data', {
            'fields': ('bus', 'latitude', 'longitude', 'speed')
        }),
        ('Additional Info', {
            'fields': ('accuracy', 'battery_level', 'timestamp'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'geofence_type', 'center_latitude', 'center_longitude', 'radius', 'is_active')
    list_filter = ('geofence_type', 'is_active')
    search_fields = ('name',)

@admin.register(GeofenceEvent)
class GeofenceEventAdmin(admin.ModelAdmin):
    list_display = ('bus', 'geofence', 'event_type', 'timestamp')
    list_filter = ('event_type', 'geofence', 'timestamp')
    search_fields = ('bus__bus_number', 'geofence__name')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('bus', 'start_time', 'end_time', 'status', 'total_distance', 'passenger_count')
    list_filter = ('status', 'start_time', 'bus')
    search_fields = ('bus__bus_number',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Trip Information', {
            'fields': ('bus', 'schedule', 'status', 'passenger_count')
        }),
        ('Time & Location', {
            'fields': ('start_time', 'end_time', 'start_latitude', 'start_longitude',
                      'end_latitude', 'end_longitude')
        }),
        ('Metrics', {
            'fields': ('total_distance', 'average_speed')
        }),
    )

@admin.register(TripPoint)
class TripPointAdmin(admin.ModelAdmin):
    list_display = ('trip', 'sequence', 'latitude', 'longitude', 'speed', 'timestamp')
    list_filter = ('trip',)
    search_fields = ('trip__bus__bus_number',)
    readonly_fields = ('timestamp',)