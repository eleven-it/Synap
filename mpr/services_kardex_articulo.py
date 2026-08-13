"""Kardex artículo MPR: movimiento_stock OPP/OPA por depósito (extraído de services.py por tamaño)."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_int_or_none,
)

logger = logging.getLogger(__name__)

ClasificacionKardex = Literal["entrada", "salida", "ignorar"]

MOTIVO_PARTE_PRODUCCION = "Parte producción"


def _clasificar_movimiento_kardex(
    tipo_mov: Optional[str],
    motivo_movimiento: Optional[str],
) -> ClasificacionKardex:
    """Clasifica movimiento MSTOCK para kardex: OPP/legacy → entrada, OPA/ARMADO → salida."""
    tipo = (tipo_mov or "").strip().upper()
    motivo = (motivo_movimiento or "").strip()

    if tipo == "OPT":
        return "ignorar"
    if tipo == "OPP" or motivo == MOTIVO_PARTE_PRODUCCION:
        return "entrada"
    if tipo in ("OPA", "ARMADO"):
        return "salida"
    return "ignorar"


def _fmt_fecha_display_kardex(value: Any) -> str:
    """Fecha dd/MM/yyyy para UI kardex."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    parsed = to_date_or_none(value)
    if parsed:
        try:
            dt = datetime.strptime(str(parsed)[:10], "%Y-%m-%d").date()
            return dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            pass
    return str_or_default(value, "")


def _calcular_saldo_corrido_movimientos(
    movimientos: List[Dict[str, Any]],
    *,
    saldo_inicial: int = 0,
) -> List[Dict[str, Any]]:
    """Acumula saldo_corrido fila a fila (Σ entradas − Σ salidas desde saldo_inicial)."""
    saldo = int(saldo_inicial)
    resultado: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        entrada = int(to_int_or_none(mov.get("entrada")) or 0)
        salida = int(to_int_or_none(mov.get("salida")) or 0)
        saldo += entrada - salida
        fila = dict(mov)
        fila["saldo_corrido"] = saldo
        resultado.append(fila)
    return resultado


def _consultar_movimientos_kardex_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Filas crudas de movimiento_stock+stock para kardex (sin saldo corrido)."""
    from mpr.services import _nombre_tabla

    id_art = to_int_or_none(id_articulo)
    if not (base_empresa or "").strip() or id_art is None:
        return []

    lim = max(1, min(int(limit or 500), 5000))
    params: List[Any] = [id_art, MOTIVO_PARTE_PRODUCCION]
    filtros_extra = ""
    dep = to_int_or_none(id_deposito)
    if dep is not None:
        filtros_extra += " AND s.CodDeposito = %s"
        params.append(dep)

    fd = to_date_or_none(fecha_desde)
    fh = to_date_or_none(fecha_hasta)
    if fd:
        filtros_extra += " AND m.fecha >= %s"
        params.append(fd)
    if fh:
        filtros_extra += " AND m.fecha <= %s"
        params.append(fh)

    params.append(lim)

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return []
            cursor.execute(
                f"""
                SELECT
                    m.codigo_movimiento,
                    m.fecha,
                    m.tipo_mov,
                    m.motivo_movimiento,
                    m.nro_comprobante,
                    m.detalle,
                    m.id_operario_opt,
                    COALESCE(SUM(s.Entrada), 0) AS total_entrada,
                    COALESCE(SUM(s.Salida), 0) AS total_salida
                FROM {tbl_mov} m
                INNER JOIN {tbl_stock} s ON s.CodigoMovimiento = m.codigo_movimiento
                WHERE s.IDArt = %s
                  AND COALESCE(m.anulado, 'No') <> 'Si'
                  AND UPPER(TRIM(COALESCE(m.tipo_comprobante, ''))) = 'MSTOCK'
                  AND (
                    UPPER(TRIM(COALESCE(m.tipo_mov, ''))) = 'OPP'
                    OR COALESCE(m.motivo_movimiento, '') = %s
                    OR UPPER(TRIM(COALESCE(m.tipo_mov, ''))) IN ('OPA', 'ARMADO')
                  )
                  AND UPPER(TRIM(COALESCE(m.tipo_mov, ''))) <> 'OPT'
                  {filtros_extra}
                GROUP BY
                    m.codigo_movimiento, m.fecha, m.tipo_mov, m.motivo_movimiento,
                    m.nro_comprobante, m.detalle, m.id_operario_opt
                ORDER BY m.fecha ASC, m.codigo_movimiento ASC
                LIMIT %s
                """,
                params,
            )
            return list(cursor.fetchall() or [])
    except Exception as exc:
        logger.warning(
            "_consultar_movimientos_kardex_articulo error base=%s art=%s: %s",
            base_empresa,
            id_articulo,
            exc,
            exc_info=True,
        )
        return []


def _fetch_nombre_deposito(base_empresa: str, id_deposito: int) -> str:
    from mpr.services import _nombre_tabla

    dep = to_int_or_none(id_deposito)
    if not dep or not (base_empresa or "").strip():
        return "-"
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                return "-"
            cursor.execute(
                f"SELECT COALESCE(NombreDeposito, '') AS nombre FROM {tbl} WHERE CodDeposito = %s LIMIT 1",
                [dep],
            )
            row = cursor.fetchone()
            return str_or_default(row.get("nombre") if row else None, "-")
    except Exception:
        return "-"


def _normalizar_fila_kardex(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convierte fila SQL a movimiento kardex con entrada/salida según clasificación."""
    clasif = _clasificar_movimiento_kardex(
        row.get("tipo_mov"),
        row.get("motivo_movimiento"),
    )
    if clasif == "ignorar":
        return None

    total_entrada = int(float(row.get("total_entrada") or 0))
    total_salida = int(float(row.get("total_salida") or 0))
    if clasif == "entrada":
        entrada, salida = total_entrada, 0
    else:
        entrada, salida = 0, total_salida

    cod_mov = to_int_or_none(row.get("codigo_movimiento"))
    operario_id = to_int_or_none(row.get("id_operario_opt"))
    return {
        "fecha_display": _fmt_fecha_display_kardex(row.get("fecha")),
        "tipo_mov": str_or_default(row.get("tipo_mov"), "-"),
        "entrada": entrada,
        "salida": salida,
        "codigo_movimiento": cod_mov,
        "nro_comprobante": str_or_default(row.get("nro_comprobante"), "-"),
        "detalle": str_or_default(row.get("detalle"), ""),
        "operario": str(operario_id) if operario_id is not None else "-",
    }


def construir_kardex_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """
    Kardex MSTOCK (OPP/OPA) por artículo y depósito con saldo corrido y KPIs BOM.
    Saldo inicial de ventana = 0 (sin movimientos previos al período).
    """
    from mpr.services import (
        _fetch_descripciones_articulo,
        calcular_max_packs_armado_1ra,
        get_bom_detalle,
        get_id_en_abm_por_articulo,
    )

    id_art = to_int_or_none(id_articulo)
    vacio: Dict[str, Any] = {
        "articulo": None,
        "bom": None,
        "deposito": None,
        "movimientos": [],
        "kpis": {
            "saldo_final": 0,
            "total_entradas": 0,
            "total_salidas": 0,
            "max_packs": 0,
        },
        "advertencias": [],
    }
    if not (base_empresa or "").strip() or id_art is None:
        vacio["advertencias"] = ["Artículo no indicado."]
        return vacio

    advertencias: List[str] = []
    desc_map = _fetch_descripciones_articulo(base_empresa, [id_art])
    if id_art not in desc_map:
        advertencias.append("Artículo inexistente o sin datos en la base.")
        vacio["advertencias"] = advertencias
        return vacio

    codigo, descripcion = desc_map[id_art]
    id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_art)
    es_pack = id_en_abm is not None
    bom = get_bom_detalle(base_empresa, id_en_abm) if id_en_abm else None

    dep_id = to_int_or_none(id_deposito)
    deposito: Optional[Dict[str, Any]] = None
    if dep_id is not None:
        deposito = {
            "id": dep_id,
            "nombre": _fetch_nombre_deposito(base_empresa, dep_id),
        }

    filas_raw = _consultar_movimientos_kardex_articulo(
        base_empresa,
        id_art,
        id_deposito=dep_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
    movimientos_base: List[Dict[str, Any]] = []
    for row in filas_raw:
        fila = _normalizar_fila_kardex(row)
        if fila:
            movimientos_base.append(fila)

    movimientos = _calcular_saldo_corrido_movimientos(movimientos_base, saldo_inicial=0)
    total_entradas = sum(int(m.get("entrada") or 0) for m in movimientos)
    total_salidas = sum(int(m.get("salida") or 0) for m in movimientos)
    saldo_final = total_entradas - total_salidas
    if movimientos:
        saldo_final = int(movimientos[-1].get("saldo_corrido") or 0)

    max_packs = 0
    if es_pack and dep_id is not None:
        max_packs = max(
            0,
            int(
                calcular_max_packs_armado_1ra(
                    base_empresa,
                    id_art,
                    deposito_semi=dep_id,
                )
                or 0
            ),
        )

    return {
        "articulo": {
            "id": id_art,
            "codigo": codigo,
            "descripcion": descripcion,
            "es_pack": es_pack,
            "id_en_abm": id_en_abm,
        },
        "bom": bom,
        "deposito": deposito,
        "movimientos": movimientos,
        "kpis": {
            "saldo_final": saldo_final,
            "total_entradas": total_entradas,
            "total_salidas": total_salidas,
            "max_packs": max_packs,
        },
        "advertencias": advertencias,
    }
