from django.contrib import admin
from logistics.models import LogisticsConfig, NotificationConfig, Geofence, DriverLocation, TrackingConfig

@admin.register(LogisticsConfig)
class LogisticsConfigAdmin(admin.ModelAdmin):
    list_display = ['weather_provider', 'use_traccar', 'use_smartphone_tracking', 'updated_at']
    readonly_fields = ['updated_at']

@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'receive_push', 'receive_email', 'created_at']
    list_filter = ['receive_push', 'receive_email', 'role']

@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ['name', 'center_lat', 'center_lon', 'radius', 'is_active']
    list_filter = ['is_active']

@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = ['driver', 'latitude', 'longitude', 'timestamp', 'accuracy']
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']

@admin.register(TrackingConfig)
class TrackingConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'tracking_type', 'is_active', 'created_at']
    list_filter = ['tracking_type', 'is_active'] 