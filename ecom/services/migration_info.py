"""
Metadatos de paridad con docs/ecom/REVERSE_ENGINEERING.md.
Si el inventario PHP cambia, actualizar constantes y el documento.

Repo: git@github.com:licPflores/administraNET-ecom.git
"""

# Inventario al 2026-03-30 (clon = remoto anterior; alineado a backup Synap BKP 2025-11-19)
PHP_FILE_COUNT = 1287
# Solo mayoristapp/ (excluye ~11 .php en raíz del repo)
MAYORISTAPP_PHP_FILE_COUNT = 1276
RELAY_ENDPOINT_COUNT = 44
FRAMEWORK_LABEL = "procedural_php_mysqli"
SOURCE_LABEL = "administraNET-ecom"


def _checkpoints_mayoristapp() -> list:
    """
    Filas ``EcomMigrationCheckpoint`` (Fase C — cierre por vertical).
    Lista vacía si el modelo no está disponible o falla la consulta (tests sin BD).
    """
    try:
        from django.apps import apps

        if not apps.ready:
            return []
        from ecom.models import EcomMigrationCheckpoint

        out = []
        for o in EcomMigrationCheckpoint.objects.order_by("module_slug").all():
            out.append(
                {
                    "module_slug": o.module_slug,
                    "notes": (o.notes or "")[:500],
                    "updated_at": o.updated_at.isoformat() if o.updated_at else None,
                }
            )
        return out
    except Exception:
        return []


def build_migration_info_dict() -> dict:
    """Devuelve el dict expuesto por /ecom/api/migration-info/."""
    return {
        "php_file_count": PHP_FILE_COUNT,
        "mayoristapp_php_file_count": MAYORISTAPP_PHP_FILE_COUNT,
        "relay_endpoint_count": RELAY_ENDPOINT_COUNT,
        "framework": FRAMEWORK_LABEL,
        "source": SOURCE_LABEL,
        "checkpoints": _checkpoints_mayoristapp(),
    }
