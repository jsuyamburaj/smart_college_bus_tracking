from django.contrib import admin
from .models import Notification, NotificationPreference, SMSLog, EmailLog

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'title', 'priority', 'is_read', 'is_sent', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read', 'is_sent', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('created_at', 'sent_at')
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'notification_type', 'title', 'message', 'priority')
        }),
        ('Related Objects', {
            'fields': ('bus', 'route'),
            'classes': ('collapse',)
        }),
        ('Delivery Settings', {
            'fields': ('send_email', 'send_sms', 'send_push', 'scheduled_for'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'is_sent', 'sent_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_per_page = 50
    
    fieldsets = (
        ('Email Preferences', {
            'fields': (
                'email_bus_arrival', 'email_bus_delay', 'email_emergency',
                'email_route_change', 'email_maintenance', 'email_announcements'
            )
        }),
        ('SMS Preferences', {
            'fields': (
                'sms_bus_arrival', 'sms_bus_delay', 'sms_emergency', 'sms_route_change'
            )
        }),
        ('Push Notification Preferences', {
            'fields': (
                'push_bus_arrival', 'push_bus_delay', 'push_emergency',
                'push_route_change', 'push_maintenance', 'push_announcements'
            )
        }),
        ('Quiet Hours', {
            'fields': ('respect_quiet_hours', 'quiet_hours_start', 'quiet_hours_end')
        }),
    )

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone_number', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'sent_at', 'created_at')
    search_fields = ('phone_number', 'message', 'provider_message_id')
    readonly_fields = ('created_at', 'sent_at', 'delivered_at')
    list_per_page = 50

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'subject', 'status', 'sent_at', 'created_at')
    list_filter = ('status', 'sent_at', 'created_at')
    search_fields = ('email', 'subject', 'message', 'provider_message_id')
    readonly_fields = ('created_at', 'sent_at')
    list_per_page = 50