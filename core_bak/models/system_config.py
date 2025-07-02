from django.db import models
from django.utils.translation import gettext_lazy as _

class SystemConfiguration(models.Model):
    key = models.CharField(
        max_length=255, 
        unique=True, 
        help_text=_("The unique key for the configuration (e.g. 'main.site.name').")
    )
    value = models.TextField(
        blank=True,
        help_text=_("The value of the configuration.")
    )
    description = models.CharField(
        max_length=255, 
        blank=True, 
        help_text=_("Description of what this configuration does.")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Indicates if this configuration is active and in use.")
    )

    class Meta:
        verbose_name = _("System Configuration")
        verbose_name_plural = _("System Configurations")

    def __str__(self):
        return self.key
