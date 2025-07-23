from django.db import models
from django.utils.translation import gettext_lazy as _

class LogisticsConfig(models.Model):
    weather_api_key = models.CharField(_('Weather API Key'), max_length=128, blank=True, null=True, help_text=_('API key for OpenWeatherMap or other weather provider'))
    weather_provider = models.CharField(_('Weather Provider'), max_length=64, default='openweathermap', help_text=_('Weather API provider'))
    traccar_api_url = models.URLField(_('Traccar API URL'), blank=True, null=True)
    traccar_api_token = models.CharField(_('Traccar API Token'), max_length=128, blank=True, null=True)
    use_traccar = models.BooleanField(_('Enable Traccar Integration'), default=False)
    use_smartphone_tracking = models.BooleanField(_('Enable Smartphone Tracking'), default=True)
    google_maps_api_key = models.CharField(_('Google Maps API Key'), max_length=128, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Logistics Configuration')
        verbose_name_plural = _('Logistics Configurations')

    def __str__(self):
        return _('Logistics Global Configuration') 