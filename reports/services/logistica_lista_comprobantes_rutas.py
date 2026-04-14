"""
Compatibilidad: el dominio vive en ``logistica.services.lista_comprobantes_rutas``.

Los informes y código existente pueden seguir importando desde ``reports.services``.
"""

from logistica.services.lista_comprobantes_rutas import (  # noqa: F401
    MOTIVOS_NO_ENTREGA,
    SQL_DETALLE_REMITO,
    autocomplete_clientes,
    build_listado_sql_and_params,
    debe_restringir_por_chofer,
    detalle_no_entrega_cumple,
    ejecutar_listado,
    guardar_entrega,
    listar_motivos_no_entrega_catalogo,
    listar_motivos_no_entrega_descripciones,
    motivo_no_entrega_es_valido,
    obtener_detalle_remito,
    resolve_base_empresa,
    resolve_id_usuario_from_user,
)
