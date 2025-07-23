from django.db import models
from django.utils.translation import gettext_lazy as _

class Geofence(models.Model):
    name = models.CharField(_('Name'), max_length=64)
    description = models.TextField(_('Description'), blank=True)
    # Polygon: lista de puntos lat/lng en formato GeoJSON
    polygon = models.JSONField(_('Polygon'), blank=True, null=True, help_text=_('GeoJSON coordinates for polygon geofence'))
    # Circle: centro y radio
    center_lat = models.FloatField(_('Center Latitude'), blank=True, null=True)
    center_lng = models.FloatField(_('Center Longitude'), blank=True, null=True)
    radius_m = models.FloatField(_('Radius (meters)'), blank=True, null=True)
    # Asociación opcional
    route = models.ForeignKey('logistics.DeliveryRoute', on_delete=models.SET_NULL, null=True, blank=True, related_name='geofences')
    vehicle = models.ForeignKey('logistics.Vehicle', on_delete=models.SET_NULL, null=True, blank=True, related_name='geofences')
    client_id = models.IntegerField(_('Client ID'), blank=True, null=True)
    active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name 