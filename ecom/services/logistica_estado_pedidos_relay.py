"""
Paridad ``ajax/json_pantalla_pedidos.php`` — datos para la pantalla **Estado de pedidos**
(logística / preparación, tablero tipo Kanban).

Origen legado: ``mayoristapp/logistica_pantalla_preparacion.php`` + JSON AJAX.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool, mysql_cursor
from core.utils.administranet_types import to_int_or_none

from ecom.services.credito_pedidos.aprobacion import puede_avanzar_a_preparacion
from ecom.services.ecom_config_mysql import credito_pedidos_activo


def _filtro_sucursal_sql(cod_sucursal: Optional[int]) -> tuple[str, List[Any]]:
    if cod_sucursal is None:
        return "", []
    return " AND pedido.CodSucursal = %s ", [cod_sucursal]


def listar_sucursales_tv(*, base_empresa: str) -> List[Dict[str, Any]]:
    """SELECT id_sucursal, nombre_sucursal, domicilio_sucursal FROM sucursales (misma forma que PHP)."""
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    sql = """
        SELECT id_sucursal, nombre_sucursal, domicilio_sucursal
        FROM sucursales
        ORDER BY id_sucursal ASC
    """
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(sql)
        cols = [d[0] for d in c.description] if c.description else []
        for row in c.fetchall():
            item = dict(zip(cols, row))
            out.append(
                {
                    "id_sucursal": item.get("id_sucursal"),
                    "nombre_sucursal": item.get("nombre_sucursal") or "",
                    "domicilio_sucursal": item.get("domicilio_sucursal") or "",
                }
            )
    return out


def estado_pedidos_kanban_json(
    *,
    base_empresa: str,
    cod_sucursal: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Devuelve las mismas claves que el JSON PHP::

        en_preparacion, preparado, en_remito

    Notas de paridad:
    - ``En preparación`` en BD puede aparecer como ``En preparacion`` (sin tilde), como en el PHP original.
    - Columna **preparado** en PHP solo incluye ``comprobante`` (sin ``usuario``).
    """
    filtro_sql, filtro_params = _filtro_sucursal_sql(cod_sucursal)

    sql_en_prep = f"""
        SELECT
            pedido.NroComprobante AS nroPedido,
            CONCAT(
                COALESCE(usuario_prepara.apellido_usuario, ''), ' ',
                COALESCE(usuario_prepara.nombre_usuario, ''), ' (',
                COALESCE(usuario_prepara.cod_usuario, ''), ')'
            ) AS persona
        FROM comp_ped AS pedido
        LEFT JOIN usuarios AS usuario_prepara
            ON usuario_prepara.id_usuario = pedido.id_usuario_preparacion
        WHERE pedido.Estado IN ('En preparacion', 'En preparación')
        {filtro_sql}
        ORDER BY pedido.fecha_hora_fin_preparacion ASC
    """

    sql_preparado = f"""
        SELECT pedido.NroComprobante AS nroPedido
        FROM comp_ped AS pedido
        LEFT JOIN usuarios AS usuario_prepara
            ON usuario_prepara.id_usuario = pedido.id_usuario_preparacion
        WHERE pedido.Estado = 'Preparado'
        {filtro_sql}
        ORDER BY pedido.fecha_hora_fin_preparacion ASC
    """

    sql_remito = f"""
        SELECT
            pedido.NroComprobante AS nroPedido,
            CONCAT(
                COALESCE(usuario_prepara.apellido_usuario, ''), ' ',
                COALESCE(usuario_prepara.nombre_usuario, ''), ' (',
                COALESCE(usuario_prepara.cod_usuario, ''), ')'
            ) AS persona
        FROM comp_ped AS pedido
        LEFT JOIN rem_ped ON rem_ped.codmov_pedido = pedido.CodigoMovimiento
        LEFT JOIN comp_ped AS remito ON remito.CodigoMovimiento = rem_ped.codmov_remito
        LEFT JOIN usuarios AS usuario_prepara
            ON usuario_prepara.id_usuario = pedido.id_usuario_preparacion
        WHERE rem_ped.Anulado = 'No'
          AND pedido.Estado = 'En remito'
          AND remito.Estado = 'Pendiente'
        {filtro_sql}
        ORDER BY remito.fecha_control ASC
    """

    en_preparacion: List[Dict[str, Any]] = []
    preparado: List[Dict[str, Any]] = []
    en_remito: List[Dict[str, Any]] = []

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()

        c.execute(sql_en_prep, filtro_params)
        cols = [d[0] for d in c.description] if c.description else []
        for row in c.fetchall():
            r = dict(zip(cols, row))
            persona = (r.get("persona") or "").strip()
            if persona in ("()", "( )"):
                persona = ""
            en_preparacion.append(
                {
                    "comprobante": str(r.get("nroPedido") or ""),
                    "usuario": persona,
                }
            )

        c.execute(sql_preparado, filtro_params)
        cols_p = [d[0] for d in c.description] if c.description else []
        for row in c.fetchall():
            r = dict(zip(cols_p, row))
            preparado.append({"comprobante": str(r.get("nroPedido") or "")})

        c.execute(sql_remito, filtro_params)
        cols_r = [d[0] for d in c.description] if c.description else []
        for row in c.fetchall():
            r = dict(zip(cols_r, row))
            persona = (r.get("persona") or "").strip()
            if persona in ("()", "( )"):
                persona = ""
            en_remito.append(
                {
                    "comprobante": str(r.get("nroPedido") or ""),
                    "usuario": persona,
                }
            )

    return {
        "en_preparacion": en_preparacion,
        "preparado": preparado,
        "en_remito": en_remito,
    }


def parse_cod_sucursal_request(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    return to_int_or_none(value)


def validar_gate_credito_preparacion(base_empresa: str, cod_mov: int) -> tuple[bool, str]:
    """
    Gate Synap antes de transicionar un PED a «En preparación».
    Delega en ``puede_avanzar_a_preparacion`` cuando el workflow de crédito está activo.
    """
    if not credito_pedidos_activo(base_empresa):
        return True, ""
    try:
        with mysql_cursor(base_empresa) as cursor:
            return puede_avanzar_a_preparacion(cursor, int(cod_mov))
    except Exception:
        return True, ""
