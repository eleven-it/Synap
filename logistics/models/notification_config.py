from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class NotificationConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='logistics_notification_configs')
    role = models.CharField(_('Role'), max_length=64, blank=True, null=True)
    receive_push = models.BooleanField(_('Push Notifications'), default=True)
    receive_email = models.BooleanField(_('Email Notifications'), default=True)
    events = models.JSONField(_('Event Types'), default=list, help_text=_('List of event types to notify (e.g. delayed, out_geofence, incident, completed)'))
    channels = models.JSONField(_('Preferred Channels'), default=list, help_text=_('List of preferred channels (push, email, sms, etc.)'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Logistics Notification Config')
        verbose_name_plural = _('Logistics Notification Configs')

    def __str__(self):
        return f"NotificationConfig for {self.user or self.role or 'All'}" 