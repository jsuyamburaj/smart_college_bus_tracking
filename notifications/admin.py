from django.contrib import admin
from .models import Notification, NotificationPreference, NotificationLog, NotificationTemplate

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'title', 'priority', 'is_read', 'is_sent', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read', 'is_sent', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at', 'sent_at', 'read_at')
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'notification_type', 'title', 'message', 'priority')
        }),
        ('Related Objects', {
            'fields': ('bus', 'route', 'trip'),
            'classes': ('collapse',)
        }),
        ('Delivery Settings', {
            'fields': ('send_email', 'send_sms', 'send_push', 'scheduled_for', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'is_sent', 'read_at', 'sent_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'resend_selected']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"{queryset.count()} notifications marked as read.")
    mark_as_read.short_description = "Mark selected as read"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"{queryset.count()} notifications marked as unread.")
    mark_as_unread.short_description = "Mark selected as unread"
    
    def resend_selected(self, request, queryset):
        from .tasks import send_notification
        for notification in queryset.filter(is_sent=False):
            send_notification.delay(notification.id)
        self.message_user(request, f"{queryset.count()} notifications queued for sending.")
    resend_selected.short_description = "Resend selected"

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_per_page = 50
    
    fieldsets = (
        ('Email Preferences', {
            'fields': (
                'email_bus_arrival', 'email_bus_delay', 'email_emergency',
                'email_route_change', 'email_maintenance', 'email_announcements', 'email_system'
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
                'push_route_change', 'push_maintenance', 'push_announcements', 'push_system'
            )
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end')
        }),
        ('Rate Limits', {
            'fields': ('max_notifications_per_hour', 'max_emails_per_day')
        }),
    )

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'notification', 'delivery_method', 'status', 'created_at')
    list_filter = ('delivery_method', 'status', 'created_at')
    search_fields = ('notification__user__username', 'provider_message_id')
    readonly_fields = ('created_at', 'sent_at', 'delivered_at')
    list_per_page = 50

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'notification_type', 'is_active', 'created_at')
    list_filter = ('notification_type', 'is_active')
    search_fields = ('name', 'title_template', 'message_template')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'is_active', 'variables')
        }),
        ('Templates', {
            'fields': ('title_template', 'message_template')
        }),
        ('Email Template', {
            'fields': ('email_subject_template', 'email_body_template'),
            'classes': ('collapse',)
        }),
        ('SMS Template', {
            'fields': ('sms_template'),
            'classes': ('collapse',)
        }),
        ('Push Template', {
            'fields': ('push_template'),
            'classes': ('collapse',)
        }),
    )