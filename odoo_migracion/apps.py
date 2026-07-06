from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OdooMigracionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "odoo_migracion"
    verbose_name = _("Migración Odoo")
