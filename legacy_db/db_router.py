"""
Router para que los modelos de legacy_db (managed=False) usen la base MySQL administraNET.
Las escrituras reales se hacen vía repositories con get_connection(base_empresa).
"""


class LegacyDbRouter:
    """Enruta legacy_db a la base de datos 'mysql'."""

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "legacy_db":
            return "mysql"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "legacy_db":
            return "mysql"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == "legacy_db" or obj2._meta.app_label == "legacy_db":
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == "legacy_db":
            return False  # managed=False, no migraciones
        return None
