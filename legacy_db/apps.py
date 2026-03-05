from django.apps import AppConfig


class LegacyDbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legacy_db"
    verbose_name = "Legacy DB (escritura compatible VB6 - administraNET)"
