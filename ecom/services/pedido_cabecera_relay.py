"""
Cabecera, pedidos recientes y vínculos de un PED (gestión comercial Synap).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import to_int_or_none

from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario
from ecom.services.comprobantes_relay import _fetch_all
from ecom.services.pedido_permisos import puede_ver_todos_pedidos

_ESTADOS_ANULABLES = ("Pendiente",)


def cabecera_pedido_relay(base_empresa: str, cod_mov: int) -> Optional[Dict[str, Any]]:
    """Cabecera ``comp_ped`` + cliente, viajante y datos adicionales."""
    cod = to_int_or_none(cod_mov)
    if cod is None:
        return None
    sql = """
        SELECT
            cp.CodigoMovimiento AS codigo_movimiento,
            cp.TipoComprobante AS tipo_comprobante,
            cp.NroComprobante AS nro_comprobante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Fecha AS fecha_iso,
            cp.Estado AS estado,
            cp.Anulado AS anulado,
            cp.Codigo AS id_cliente,
            cp.CodViajante AS cod_viajante,
            cp.CodSucursal AS cod_sucursal,
            cp.id_pv AS id_punto_venta,
            cp.TipoPedido AS tipo_pedido,
            cp.Detalle AS observaciones,
            cp.CondVenta AS cond_venta,
            DATE_FORMAT(cp.FechaEntrega, '%%d/%%m/%%Y') AS fecha_entrega,
            cp.FormaEntrega AS forma_entrega,
            cp.autorizacion_sistema AS autorizacion_sistema,
            cp.autorizacion_web AS autorizacion_web,
            cp.ImporteVenta AS importe_venta,
            cp.SubTotal1 AS subtotal_1,
            cp.SubTotal2 AS subtotal_2,
            cp.Exento AS exento,
            cp.IVA1 AS iva_1,
            cp.IVA2 AS iva_2,
            cp.impuesto_interno_total AS impuesto_interno_total,
            cp.total_percep AS total_percep,
            cp.SubtotalDesc AS subtotal_desc,
            (cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)) AS total,
            cliente.nombre_cliente AS nombre_cliente,
            cliente.Email AS email_cliente,
            cliente.id_manual_cli AS id_manual_cli,
            CONCAT(viajantes.CodViajante, ' - ', viajantes.Nombre) AS nombre_viajante,
            cda.fechaEntrega AS cda_fecha_entrega,
            cda.id_cliente_domicilio AS id_cliente_domicilio,
            cda.id_ruta AS id_ruta,
            cda.Fentrega AS cda_forma_entrega
        FROM comp_ped cp
        LEFT JOIN cliente ON cliente.Codigo = cp.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = cp.CodViajante
        LEFT JOIN cliente_datos_adicionales cda ON cda.CodigoMovimiento = cp.CodigoMovimiento
        WHERE cp.CodigoMovimiento = %s AND cp.TipoComprobante = 'PED'
        LIMIT 1
    """
    rows = _fetch_all(base_empresa, sql, [cod])
    return rows[0] if rows else None


def cabecera_comp_ped_relay(base_empresa: str, cod_mov: int) -> Optional[Dict[str, Any]]:
    """Cabecera comp_ped por CodigoMovimiento (PED, PRE o DEV)."""
    cod = to_int_or_none(cod_mov)
    if cod is None:
        return None
    sql = """
        SELECT
            cp.CodigoMovimiento AS codigo_movimiento,
            cp.TipoComprobante AS tipo_comprobante,
            cp.NroComprobante AS nro_comprobante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Fecha AS fecha_iso,
            cp.Estado AS estado,
            cp.Anulado AS anulado,
            cp.Codigo AS id_cliente,
            cp.CodViajante AS cod_viajante,
            cp.CodSucursal AS cod_sucursal,
            cp.id_pv AS id_punto_venta,
            cp.TipoPedido AS tipo_pedido,
            cp.Detalle AS observaciones,
            cp.CondVenta AS cond_venta,
            DATE_FORMAT(cp.FechaEntrega, '%%d/%%m/%%Y') AS fecha_entrega,
            cp.FormaEntrega AS forma_entrega,
            cp.autorizacion_sistema AS autorizacion,
            (cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)) AS total,
            cliente.nombre_cliente AS nombre_cliente,
            cliente.Email AS email_cliente,
            viajantes.Nombre AS nombre_viajante,
            cda.Fentrega AS cda_forma_entrega
        FROM comp_ped cp
        LEFT JOIN cliente ON cliente.Codigo = cp.Codigo
        LEFT JOIN viajantes ON viajantes.CodViajante = cp.CodViajante
        LEFT JOIN cliente_datos_adicionales cda ON cda.CodigoMovimiento = cp.CodigoMovimiento
        WHERE cp.CodigoMovimiento = %s
        LIMIT 1
    """
    rows = _fetch_all(base_empresa, sql, [cod])
    return rows[0] if rows else None


def pedidos_recientes_relay(
    base_empresa: str,
    id_cliente: int,
    *,
    limit: int = 10,
    incluir_importe: bool = True,
) -> List[Dict[str, Any]]:
    """Últimos PED no anulados del cliente (bloque compra / repetir)."""
    lim = max(1, min(int(limit), 50))
    cols = """
            cp.CodigoMovimiento AS codigo_movimiento,
            cp.NroComprobante AS nro_comprobante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Estado AS estado
    """
    if incluir_importe:
        cols += """,
            (cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)) AS total
        """
    sql = f"""
        SELECT {cols}
        FROM comp_ped cp
        WHERE cp.TipoComprobante = 'PED'
          AND cp.Anulado = 'No'
          AND cp.Codigo = %s
        ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
        LIMIT %s
    """
    return _fetch_all(base_empresa, sql, [int(id_cliente), lim])


def vinculos_pedido_relay(base_empresa: str, cod_mov: int) -> List[Dict[str, Any]]:
    """Remitos vinculados al pedido vía ``rem_ped``."""
    cod = to_int_or_none(cod_mov)
    if cod is None:
        return []
    sql = """
        SELECT
            rem.CodigoMovimiento AS codigo_movimiento_remito,
            rem.NroComprobante AS nro_comprobante,
            rem.Estado AS estado,
            DATE_FORMAT(rem.Fecha, '%%d/%%m/%%Y') AS fecha
        FROM rem_ped rp
        INNER JOIN comp_ped rem ON rem.CodigoMovimiento = rp.codmov_remito
        WHERE rp.codmov_pedido = %s AND rp.Anulado = 'No'
        ORDER BY rem.Fecha ASC
    """
    return _fetch_all(base_empresa, sql, [cod])


def puede_anular_pedido_relay(base_empresa: str, cod_mov: int) -> Tuple[bool, str]:
    """Solo PED no anulado en estado Pendiente."""
    cab = cabecera_pedido_relay(base_empresa, cod_mov)
    if not cab:
        return False, "Pedido no encontrado."
    if str(cab.get("anulado") or "").strip().lower() in ("si", "sí"):
        return False, "El pedido ya está anulado."
    estado = str(cab.get("estado") or "").strip()
    if estado not in _ESTADOS_ANULABLES:
        return False, f"No se puede anular un pedido en estado «{estado}»."
    return True, ""


def pedidos_kpis_relay(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    idcliente: Optional[int] = None,
) -> Dict[str, Any]:
    """KPIs del día para hub pedidos (PED no anulados)."""
    where = ["cp.TipoComprobante = 'PED'", "cp.Anulado = 'No'", "DATE(cp.Fecha) = CURDATE()"]
    params: List[Any] = []
    tipousuario = (sess_user.get("tipousuario") or "").strip().lower()
    if tipousuario == "cliente" and idcliente is not None:
        where.append("cp.Codigo = %s")
        params.append(int(idcliente))
    elif tipousuario != "cliente":
        if not puede_ver_todos_pedidos(sess_user):
            cv = cod_viajante_desde_sesion_usuario(sess_user)
            if cv is not None:
                where.append("cp.CodViajante = %s")
                params.append(cv)
    sql = f"""
        SELECT
            COUNT(*) AS pedidos_hoy,
            SUM(CASE WHEN TRIM(cp.autorizacion_sistema) = 'No Autorizado' THEN 1 ELSE 0 END) AS no_autorizados,
            COALESCE(SUM(cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)), 0) AS total_monto
        FROM comp_ped cp
        WHERE {' AND '.join(where)}
    """
    rows = _fetch_all(base_empresa, sql, params)
    row = rows[0] if rows else {}
    return {
        "pedidos_hoy": int(row.get("pedidos_hoy") or 0),
        "no_autorizados": int(row.get("no_autorizados") or 0),
        "total_monto": float(row.get("total_monto") or 0),
    }


def stepper_estados_pedido(estado_actual: str) -> List[Dict[str, Any]]:
    """Pasos del ciclo comercial para UI (solo lectura)."""
    pasos = [
        ("pendiente", "Pendiente"),
        ("preparacion", "En preparación"),
        ("preparado", "Preparado"),
        ("remito", "En remito"),
        ("cerrado", "Cerrado / Facturado"),
    ]
    actual = (estado_actual or "Pendiente").strip().lower()
    out: List[Dict[str, Any]] = []
    orden = 0
    activo_idx = 0
    for key, label in pasos:
        activo = False
        if key == "pendiente" and actual in ("pendiente",):
            activo = True
        elif key == "preparacion" and actual in ("en preparación", "en preparacion"):
            activo = True
        elif key == "preparado" and actual == "preparado":
            activo = True
        elif key == "remito" and actual in ("en remito", "parcial"):
            activo = True
        elif key == "cerrado" and actual in ("cerrado", "facturado"):
            activo = True
        if activo:
            activo_idx = orden
        out.append({"clave": key, "etiqueta": label, "activo": activo, "orden": orden})
        orden += 1
    for i, item in enumerate(out):
        item["completado"] = i < activo_idx
    return out
