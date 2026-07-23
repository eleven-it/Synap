from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals
        from core.pyafipws_errno_compat import apply_pyafipws_errno_compat
        from core.backup import models as backup_models  # noqa: F401

        apply_pyafipws_errno_compat()