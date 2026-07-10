"""
Conversión de presupuesto (PRE) a pedido (PED) — paridad VB6 ``Pedido.frm``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

from ecom.models import EcomCart
from ecom.services.comprobantes_relay import _fetch_all, detalle_pedido_relay
from ecom.services.mayorista_cart_service import agregar_item, limpiar, obtener_o_crear_carrito
from ecom.services.mayorista_checkout_service import CheckoutInput, confirmar


def cabecera_comprobante_relay(
    base_empresa: str,
    cod_mov: int,
    *,
    tipo_comprobante: str = "PRE",
) -> Optional[Dict[str, Any]]:
    """Cabecera ``comp_ped`` para PRE o PED."""
    cod = to_int_or_none(cod_mov)
    tipo = (tipo_comprobante or "PRE").strip().upper()
    if cod is None:
        return None
    sql = """
        SELECT
            cp.CodigoMovimiento AS codigo_movimiento,
            cp.TipoComprobante AS tipo_comprobante,
            cp.NroComprobante AS nro_comprobante,
            cp.Estado AS estado,
            cp.Anulado AS anulado,
            cp.Codigo AS id_cliente,
            cp.id_pv AS id_punto_venta,
            cp.id_deposito_despacho AS id_deposito,
            cp.FormaEntrega AS forma_entrega,
            cp.Detalle AS observaciones,
            cliente.descuento_por_cli AS descuento_cliente
        FROM comp_ped cp
        LEFT JOIN cliente ON cliente.Codigo = cp.Codigo
        WHERE cp.CodigoMovimiento = %s AND cp.TipoComprobante = %s
        LIMIT 1
    """
    rows = _fetch_all(base_empresa, sql, [cod, tipo])
    return rows[0] if rows else None


def _ya_convertido(base_empresa: str, cod_mov_pre: int) -> bool:
    sql_pp = """
        SELECT 1 FROM ped_presup
        WHERE codigo_movimiento_presup = %s AND COALESCE(anulado, 'No') = 'No'
        LIMIT 1
    """
    if _fetch_all(base_empresa, sql_pp, [cod_mov_pre]):
        return True
    sql_st = """
        SELECT 1 FROM stockp
        WHERE codmov_presupuesto = %s AND Anulado = 'No'
        LIMIT 1
    """
    return bool(_fetch_all(base_empresa, sql_st, [cod_mov_pre]))


def validar_presupuesto_convertible(
    base_empresa: str,
    cod_mov_pre: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Valida PRE convertible a PED."""
    cab = cabecera_comprobante_relay(base_empresa, cod_mov_pre, tipo_comprobante="PRE")
    if not cab:
        return None, "Presupuesto no encontrado."
    if str(cab.get("anulado") or "").strip().lower() in ("si", "sí"):
        return None, "El presupuesto está anulado."
    estado = str(cab.get("estado") or "").strip()
    if estado.lower() in ("en pedido",):
        return None, "El presupuesto ya fue convertido a pedido."
    if _ya_convertido(base_empresa, cod_mov_pre):
        return None, "Ya existe un pedido vinculado a este presupuesto."
    renglones = detalle_pedido_relay(base_empresa, cod_mov_pre)
    if not renglones:
        return None, "El presupuesto no tiene renglones."
    return cab, None


def convertir_presupuesto_a_pedido(
    base_empresa: str,
    cod_mov_pre: int,
    *,
    id_usuario: int,
    id_punto_venta: int,
    cod_viajante: Optional[int] = None,
    es_cliente: bool = False,
    forma_entrega: str = "",
    observaciones: str = "",
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Carga renglones del PRE al carrito, confirma PED y vincula ``ped_presup``.
    """
    cab, err = validar_presupuesto_convertible(base_empresa, cod_mov_pre)
    if err:
        return False, err, None

    id_cliente = to_int_or_none(cab.get("id_cliente"))
    if id_cliente is None:
        return False, "Presupuesto sin cliente.", None

    id_dep = to_int_or_none(cab.get("id_deposito")) or 1
    desc_cli = to_decimal_or_none(cab.get("descuento_cliente")) or Decimal("0")

    cart = obtener_o_crear_carrito(
        base_empresa,
        id_usuario,
        idcliente=id_cliente,
        id_deposito=id_dep,
        tipo_comprobante=EcomCart.TIPO_PEDIDO,
    )
    limpiar(cart)

    renglones = detalle_pedido_relay(base_empresa, cod_mov_pre)
    agregados = 0
    for r in renglones:
        id_art = to_int_or_none(r.get("IDArt"))
        cant = to_decimal_or_none(r.get("Salida"))
        if id_art is None or cant is None or cant <= 0:
            continue
        _item, e = agregar_item(
            cart,
            id_art,
            cant,
            descuento_cliente=desc_cli,
        )
        if e:
            return False, e, None
        agregados += 1

    if agregados == 0:
        return False, "No hay artículos válidos para convertir.", None

    datos = CheckoutInput(
        tipo=EcomCart.TIPO_PEDIDO,
        id_punto_venta=id_punto_venta,
        forma_entrega=forma_entrega or str(cab.get("forma_entrega") or ""),
        observaciones=observaciones or str(cab.get("observaciones") or ""),
        es_cliente=es_cliente,
        cod_mov_presupuesto_origen=cod_mov_pre,
    )
    return confirmar(cart, datos, id_usuario=id_usuario, cod_viajante=cod_viajante)


def finalizar_vinculo_presupuesto_pedido(
    cursor: Any,
    cod_mov_pre: int,
    cod_mov_ped: int,
) -> None:
    """Ejecutar dentro de la transacción de checkout tras insertar el PED."""
    cursor.execute(
        """
        UPDATE comp_ped SET Estado = 'En Pedido'
        WHERE CodigoMovimiento = %s AND TipoComprobante = 'PRE'
        """,
        [cod_mov_pre],
    )
    cursor.execute(
        "SELECT NroComprobante FROM comp_ped WHERE CodigoMovimiento = %s LIMIT 1",
        [cod_mov_pre],
    )
    row_pre = cursor.fetchone()
    nro_pre = ""
    if row_pre:
        nro_pre = row_pre[0] if not isinstance(row_pre, dict) else row_pre.get("NroComprobante")
    cursor.execute("SELECT COALESCE(MAX(id_ped_presup), 0) + 1 FROM ped_presup")
    row_id = cursor.fetchone()
    new_id = row_id[0] if row_id else 1
    cursor.execute(
        """
        INSERT INTO ped_presup
            (id_ped_presup, codigo_movimiento_ped, codigo_movimiento_presup, anulado)
        VALUES (%s, %s, %s, 'No')
        """,
        [new_id, cod_mov_ped, cod_mov_pre],
    )
    cursor.execute(
        """
        UPDATE stockp
        SET codmov_presupuesto = %s, NroPresupuesto = %s
        WHERE CodigoMovimiento = %s AND Anulado = 'No'
        """,
        [cod_mov_pre, nro_pre or "", cod_mov_ped],
    )
