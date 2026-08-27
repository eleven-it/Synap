from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MtrixAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mtrix"
    verbose_name = _("Mtrix")
