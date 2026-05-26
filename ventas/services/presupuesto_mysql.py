# -*- coding: utf-8 -*-
"""Listado y lectura de presupuestos (PRE) sobre MySQL AdministraNET (`comp_ped`)."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 25


def _norm_codigo_movimiento(val: Any) -> int:
    if val is None:
        return 0
    if isinstance(val, Decimal):
        return int(val) if val == val.to_integral_value() else int(val)
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        [name],
    )
    row = cursor.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
        """,
        [table, column],
    )
    row = cursor.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def listar_presupuestos(
    base_empresa: str,
    *,
    cod_sucursal: Optional[int] = None,
    q: str = "",
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Tuple[bool, str, List[Dict[str, Any]], int]:
    """
    Lista filas de `comp_ped` con TipoComprobante = PRE.
    """
    base_empresa = (base_empresa or "").strip()
    if not base_empresa:
        return False, "Sin base empresa.", [], 0

    page = max(1, int(page or 1))
    page_size = min(100, max(5, int(page_size or DEFAULT_PAGE_SIZE)))
    offset = (page - 1) * page_size

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "comp_ped"):
                    return False, "La tabla comp_ped no existe en esta base.", [], 0

                where = ["TipoComprobante = %s", "COALESCE(Anulado, 'No') = 'No'"]
                params: List[Any] = ["PRE"]

                if cod_sucursal is not None:
                    where.append("CodSucursal = %s")
                    params.append(int(cod_sucursal))

                q_clean = (q or "").strip()
                if q_clean:
                    where.append(
                        "(CAST(CodigoMovimiento AS CHAR) LIKE %s OR "
                        "COALESCE(NroComprobante, '') LIKE %s OR "
                        "CAST(COALESCE(Codigo, 0) AS CHAR) LIKE %s)"
                    )
                    like = f"%{q_clean}%"
                    params.extend([like, like, like])

                if fecha_desde:
                    where.append("Fecha >= %s")
                    params.append(fecha_desde)
                if fecha_hasta:
                    where.append("Fecha <= %s")
                    params.append(fecha_hasta)

                where_sql = " AND ".join(where)

                cursor.execute(
                    f"SELECT COUNT(*) FROM comp_ped WHERE {where_sql}",
                    params,
                )
                total = int(cursor.fetchone()[0] or 0)

                cursor.execute(
                    f"""
                    SELECT
                        CodigoMovimiento,
                        Fecha,
                        NroComprobante,
                        Estado,
                        Codigo,
                        ImporteVenta,
                        Detalle,
                        CodSucursal
                    FROM comp_ped
                    WHERE {where_sql}
                    ORDER BY Fecha DESC, CodigoMovimiento DESC
                    LIMIT %s OFFSET %s
                    """,
                    params + [page_size, offset],
                )

                rows: List[Dict[str, Any]] = []
                codigos_cliente = set()
                for r in cursor.fetchall():
                    cod_cli = to_int_or_none(r[4])
                    if cod_cli:
                        codigos_cliente.add(cod_cli)
                    rows.append(
                        {
                            "codigo_movimiento": _norm_codigo_movimiento(r[0]),
                            "fecha": r[1],
                            "nro_comprobante": str_or_default(r[2], "-"),
                            "estado": str_or_default(r[3], "-"),
                            "codigo_cliente": cod_cli,
                            "nombre_cliente": "",
                            "importe_venta": to_decimal_or_none(r[5]),
                            "detalle": str_or_default(r[6], ""),
                            "cod_sucursal": to_int_or_none(r[7]),
                        }
                    )

                nombres: Dict[int, str] = {}
                if codigos_cliente and _table_exists(cursor, "cliente"):
                    placeholders = ",".join(["%s"] * len(codigos_cliente))
                    cursor.execute(
                        f"""
                        SELECT Codigo, nombre_cliente
                        FROM cliente
                        WHERE Codigo IN ({placeholders})
                        """,
                        list(codigos_cliente),
                    )
                    for cr in cursor.fetchall():
                        cid = to_int_or_none(cr[0])
                        if cid:
                            nombres[cid] = str_or_default(cr[1], "-")

                for row in rows:
                    cc = row.get("codigo_cliente")
                    if cc and cc in nombres:
                        row["nombre_cliente"] = nombres[cc]
                    elif cc:
                        row["nombre_cliente"] = f"Cliente #{cc}"
                    else:
                        row["nombre_cliente"] = "—"

                return True, "", rows, total
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("listar_presupuestos: %s", e)
        return False, str(e) or "Error al listar presupuestos.", [], 0


def obtener_presupuesto_cabecera(
    base_empresa: str,
    codigo_movimiento: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Cabecera PRE por CodigoMovimiento."""
    base_empresa = (base_empresa or "").strip()
    if not base_empresa:
        return False, "Sin base empresa.", None
    try:
        cm = int(codigo_movimiento)
    except (TypeError, ValueError):
        return False, "Código de movimiento inválido.", None

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "comp_ped"):
                    return False, "La tabla comp_ped no existe en esta base.", None

                cursor.execute(
                    """
                    SELECT
                        CodigoMovimiento,
                        Fecha,
                        NroComprobante,
                        Estado,
                        Codigo,
                        ImporteVenta,
                        Detalle,
                        CodSucursal,
                        CondVenta,
                        id_condventa,
                        CodViajante,
                        Vencimiento,
                        Anulado,
                        TipoComprobante
                    FROM comp_ped
                    WHERE CodigoMovimiento = %s AND TipoComprobante = %s
                    LIMIT 1
                    """,
                    [cm, "PRE"],
                )
                r = cursor.fetchone()
                if not r:
                    return False, "Presupuesto no encontrado.", None

                cod_cli = to_int_or_none(r[4])
                nombre_cliente = "—"
                if cod_cli and _table_exists(cursor, "cliente"):
                    cursor.execute(
                        "SELECT nombre_cliente FROM cliente WHERE Codigo = %s LIMIT 1",
                        [cod_cli],
                    )
                    crow = cursor.fetchone()
                    if crow and crow[0]:
                        nombre_cliente = str_or_default(crow[0], "-")

                fecha_val = r[1]
                if isinstance(fecha_val, datetime):
                    fecha_val = fecha_val.date()

                cod_viajante_val = to_int_or_none(r[10])
                nombre_viajante = ""
                if cod_viajante_val and _table_exists(cursor, "viajantes"):
                    cursor.execute(
                        "SELECT COALESCE(Nombre, '') FROM viajantes WHERE CodViajante = %s LIMIT 1",
                        [cod_viajante_val],
                    )
                    vw = cursor.fetchone()
                    if vw:
                        nombre_viajante = str_or_default(vw[0], "").strip()

                data = {
                    "codigo_movimiento": _norm_codigo_movimiento(r[0]),
                    "fecha": fecha_val,
                    "nro_comprobante": str_or_default(r[2], "-"),
                    "estado": str_or_default(r[3], "-"),
                    "codigo_cliente": cod_cli,
                    "nombre_cliente": nombre_cliente,
                    "importe_venta": to_decimal_or_none(r[5]),
                    "detalle": str_or_default(r[6], ""),
                    "cod_sucursal": to_int_or_none(r[7]),
                    "cond_venta": str_or_default(r[8], ""),
                    "id_condventa": to_int_or_none(r[9]),
                    "cod_viajante": cod_viajante_val,
                    "nombre_viajante": nombre_viajante,
                    "vencimiento": r[11],
                    "anulado": str_or_default(r[12], "No"),
                    "tipo_comprobante": str_or_default(r[13], "PRE"),
                }
                if isinstance(data["vencimiento"], datetime):
                    data["vencimiento"] = data["vencimiento"].date()

                return True, "", data
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("obtener_presupuesto_cabecera: %s", e)
        return False, str(e) or "Error al cargar presupuesto.", None


def listar_lineas_presupuesto_stockp(
    base_empresa: str,
    codigo_movimiento: int,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Renglones en `stockp` asociados a un PRE por ``CodigoMovimiento`` de cabecera.

    Incluye casos AdministraNET donde el cuerpo quedó ligado al **pedido** generado:
    ``stockp.codmov_presupuesto`` y/o ``ped_presup`` (``codigo_movimiento_presup`` →
    ``codigo_movimiento_ped``). Sin esto, un PRE en estado «En Pedido» puede tener
    importe en ``comp_ped`` pero cero filas con ``CodigoMovimiento = PRE``.
    """
    base_empresa = (base_empresa or "").strip()
    if not base_empresa:
        return False, "Sin base empresa.", []

    try:
        cm = int(codigo_movimiento)
    except (TypeError, ValueError):
        return False, "Código de movimiento inválido.", []

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "stockp"):
                    return False, "La tabla stockp no existe en esta base.", []

                or_parts = ["CodigoMovimiento = %s"]
                params_ln: List[Any] = [cm]

                if _column_exists(cursor, "stockp", "codmov_presupuesto"):
                    or_parts.append(
                        "(codmov_presupuesto IS NOT NULL AND codmov_presupuesto <> 0 "
                        "AND codmov_presupuesto = %s)"
                    )
                    params_ln.append(cm)

                if _table_exists(cursor, "ped_presup"):
                    or_parts.append(
                        """CodigoMovimiento IN (
                            SELECT codigo_movimiento_ped FROM ped_presup
                            WHERE codigo_movimiento_presup = %s
                              AND COALESCE(anulado, 'No') = 'No'
                        )"""
                    )
                    params_ln.append(cm)

                where_sql = " COALESCE(Anulado, 'No') = 'No' AND (" + " OR ".join(or_parts) + ")"

                cursor.execute(
                    f"""
                    SELECT
                        id_stock,
                        CodigoArticulo,
                        Descripcion,
                        Cantidad,
                        Salida,
                        PrecioVentaxU,
                        PrecioNetoxR,
                        PrecioVentaxR,
                        Orden,
                        CodDeposito,
                        detalle,
                        Comprobante,
                        TipoComp
                    FROM stockp
                    WHERE {where_sql}
                    ORDER BY COALESCE(Orden, 0), id_stock
                    """,
                    params_ln,
                )
                rows: List[Dict[str, Any]] = []
                for r in cursor.fetchall():
                    cant = to_decimal_or_none(r[3])
                    salida = to_decimal_or_none(r[4])
                    qty = cant if cant is not None else salida
                    id_stock_val = r[0]
                    rows.append(
                        {
                            "id_stock": id_stock_val,
                            "id_stock_display": str(id_stock_val) if id_stock_val is not None else "",
                            "codigo_articulo": str_or_default(r[1], ""),
                            "descripcion": str_or_default(r[2], ""),
                            "cantidad": qty,
                            "precio_unitario": to_decimal_or_none(r[5]),
                            "precio_neto_renglon": to_decimal_or_none(r[6]),
                            "precio_venta_renglon": to_decimal_or_none(r[7]),
                            "orden": to_int_or_none(r[8]),
                            "cod_deposito": to_int_or_none(r[9]),
                            "detalle_renglon": str_or_default(r[10], ""),
                            "comprobante_sp": str_or_default(r[11], ""),
                            "tipo_comp_sp": str_or_default(r[12], ""),
                        }
                    )
                return True, "", rows
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("listar_lineas_presupuesto_stockp: %s", e)
        return False, str(e) or "Error al cargar renglones.", []
