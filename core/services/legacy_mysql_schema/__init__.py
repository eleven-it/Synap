"""
Herramienta global de migración de esquema MySQL (AdministraNET legacy).

Ver ``catalog.py`` para el catálogo de pasos y ``docs/general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md``.
"""

from .catalog import (
    PROVIDER_REGISTRY,
    run_all_providers,
    run_mpr_deposito_articulo_mysql,
    run_mpr_drop_lista_produccion_legacy_mysql,
    run_mpr_lista_produccion_agrupada_mysql,
    run_mpr_lista_produccion_detalle_mysql,
    run_mpr_lista_produccion_detalle_trazabilidad_mysql,
    run_mpr_core_tables_mysql,
    run_provider_by_id,
    run_self_checkout_core_tables_mysql,
    run_tiendanube_integration_mysql,
)

__all__ = [
    "PROVIDER_REGISTRY",
    "run_all_providers",
    "run_mpr_deposito_articulo_mysql",
    "run_mpr_drop_lista_produccion_legacy_mysql",
    "run_mpr_lista_produccion_agrupada_mysql",
    "run_mpr_lista_produccion_detalle_mysql",
    "run_mpr_lista_produccion_detalle_trazabilidad_mysql",
    "run_mpr_core_tables_mysql",
    "run_provider_by_id",
    "run_self_checkout_core_tables_mysql",
    "run_tiendanube_integration_mysql",
]
