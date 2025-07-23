from django.db import models
from django.utils.translation import gettext_lazy as _

class TrackingConfig(models.Model):
    """
    Configuración de tracking en tiempo real para logística.
    Permite activar integración con Traccar y/o tracking por smartphone (Google Maps).
    """
    use_traccar = models.BooleanField(
        _('Enable Traccar Integration'), default=False,
        help_text=_('Enable real-time tracking using Traccar platform')
    )
    traccar_api_url = models.URLField(
        _('Traccar API URL'), blank=True, null=True,
        help_text=_('Base URL for Traccar API (e.g., http://traccar-server:8082/api)')
    )
    traccar_api_token = models.CharField(
        _('Traccar API Token'), max_length=128, blank=True, null=True,
        help_text=_('API token for authenticating with Traccar')
    )
    use_smartphone_tracking = models.BooleanField(
        _('Enable Smartphone Tracking'), default=True,
        help_text=_('Enable real-time tracking using smartphone GPS and Google Maps')
    )
    google_maps_api_key = models.CharField(
        _('Google Maps API Key'), max_length=128, blank=True, null=True,
        help_text=_('API key for Google Maps JavaScript and Geolocation')
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Tracking Configuration')
        verbose_name_plural = _('Tracking Configurations')

    def __str__(self):
        return _('Logistics Tracking Configuration') 