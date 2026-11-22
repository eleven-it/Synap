"""
Cabecera, pedidos recientes y vínculos de un PED (gestión comercial Synap).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

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
            cp.observacion_interna AS observacion_interna,
            cp.CondVenta AS cond_venta,
            DATE_FORMAT(cp.FechaEntrega, '%%d/%%m/%%Y') AS fecha_entrega,
            cp.FechaEntrega AS fecha_entrega_iso,
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
            cliente.CUIT AS cuit_cliente,
            cliente.Email AS email_cliente,
            cliente.id_manual_cli AS id_manual_cli,
            CONCAT(viajantes.CodViajante, ' - ', viajantes.Nombre) AS nombre_viajante,
            cda.fechaEntrega AS cda_fecha_entrega,
            cda.id_cliente_domicilio AS id_cliente_domicilio,
            cda.id_transporte AS id_transporte,
            cda.id_repartidor AS id_repartidor,
            cda.operador_logistico AS operador_logistico,
            cda.nro_seguimiento AS nro_seguimiento,
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
            cp.observacion_interna AS observacion_interna,
            cp.CondVenta AS cond_venta,
            DATE_FORMAT(cp.FechaEntrega, '%%d/%%m/%%Y') AS fecha_entrega,
            cp.FechaEntrega AS fecha_entrega_iso,
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
    """Remitos del pedido y facturas asociadas vía ``rem_fact``."""
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
    remitos = _fetch_all(base_empresa, sql, [cod])
    if not remitos:
        return []
    ids = [to_int_or_none(r.get("codigo_movimiento_remito")) for r in remitos]
    ids = sorted({i for i in ids if i is not None})
    for remito in remitos:
        remito["facturas"] = []
    if not ids:
        return remitos
    placeholders = ",".join(["%s"] * len(ids))
    sql_facturas = f"""
        SELECT rf.CodigoMovimientoR AS codigo_movimiento_remito,
               fact.CodigoMovimiento AS codigo_movimiento_factura,
               fact.NroComprobante AS nro_comprobante,
               fact.TipoComprobante AS tipo_comprobante,
               DATE_FORMAT(fact.Fecha, '%%d/%%m/%%Y') AS fecha
        FROM rem_fact AS rf
        INNER JOIN cuentacliente AS fact
            ON fact.CodigoMovimiento = rf.CodigoMovimientoF
        WHERE rf.CodigoMovimientoR IN ({placeholders})
          AND COALESCE(rf.Anulado, 'No') = 'No'
          AND COALESCE(fact.Anulado, 'No') = 'No'
        ORDER BY rf.CodigoMovimientoR, fact.Fecha, fact.CodigoMovimiento
    """
    facturas = _fetch_all(base_empresa, sql_facturas, ids)
    por_remito = {to_int_or_none(r["codigo_movimiento_remito"]): r for r in remitos}
    for factura in facturas:
        remito = por_remito.get(to_int_or_none(factura.get("codigo_movimiento_remito")))
        if remito is not None:
            remito["facturas"].append(factura)
    return remitos


def entrega_renglones_pedido(
    base_empresa: str, cod_mov: int, renglones: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Anota cantidades remitas y pendientes sin alterar el PED ni sus remitos."""
    cod = to_int_or_none(cod_mov)
    if cod is None or not renglones:
        return renglones, {"estado": "sin_entrega", "pedido": 0, "entregado": 0, "pendiente": 0}
    sql = """
        SELECT s.IDArt AS id_articulo, SUM(ABS(COALESCE(s.Salida, 0))) AS entregado
        FROM stock AS s
        INNER JOIN comp_ped AS rem ON rem.CodigoMovimiento = s.codmov_remito
        WHERE s.codmov_pedido = %s
          AND rem.TipoComprobante = 'REM'
          AND COALESCE(s.Anulado, 'No') = 'No'
          AND COALESCE(rem.Anulado, 'No') = 'No'
        GROUP BY s.IDArt
    """
    entregas = _fetch_all(base_empresa, sql, [cod])
    disponible = {
        to_int_or_none(f.get("id_articulo")): to_decimal_or_none(f.get("entregado")) or Decimal("0")
        for f in entregas
    }
    salida = []
    total_pedido = Decimal("0")
    total_entregado = Decimal("0")
    for original in renglones:
        fila = dict(original)
        art = to_int_or_none(fila.get("IDArt"))
        pedido = max(to_decimal_or_none(fila.get("Salida")) or Decimal("0"), Decimal("0"))
        restante = max(disponible.get(art, Decimal("0")), Decimal("0"))
        entregado = min(pedido, restante)
        disponible[art] = restante - entregado
        pendiente = pedido - entregado
        fila["cantidad_entregada"] = entregado
        fila["cantidad_pendiente"] = pendiente
        salida.append(fila)
        total_pedido += pedido
        total_entregado += entregado
    estado = "total" if total_pedido and total_entregado >= total_pedido else (
        "parcial" if total_entregado else "sin_entrega"
    )
    return salida, {
        "estado": estado,
        "pedido": total_pedido,
        "entregado": total_entregado,
        "pendiente": total_pedido - total_entregado,
    }


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
