from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FeAfipConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fe_afip"
    verbose_name = _("Facturación Electrónica AFIP")
