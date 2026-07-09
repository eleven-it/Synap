# -*- coding: utf-8 -*-
"""Listado, filtros y cambio masivo — precios productos terminados."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import (
    str_codigo_manual_articulo,
    str_or_default,
    to_decimal_or_none,
    to_int_or_none,
)

from ventas.services.precios_articulo_legacy import (
    LISTAS_VALIDAS,
    aplicar_cambios_articulo,
    calcular_final_desde_neto,
    calcular_neto_desde_final,
    calcular_util_desde_neto,
    guardar_lote,
    q2,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 200
_BUSQUEDA_MIN_LEN = 2
Q2 = Decimal("0.01")

TIPO_TERMINADO = "Terminado"
TIPO_2DA = "Fabricado 2da"
TIPO_PRODUCTO_TERMINADO = "terminado"
TIPO_PRODUCTO_2DA = "2da"


@dataclass
class PreciosTerminadosFiltros:
    tipo_producto: str = TIPO_PRODUCTO_TERMINADO
    marcas_incluidos: List[int] = field(default_factory=list)
    codigos_incluidos: List[int] = field(default_factory=list)
    proveedores_incluidos: List[int] = field(default_factory=list)
    rubros_incluidos: List[int] = field(default_factory=list)
    subrubros_incluidos: List[int] = field(default_factory=list)
    listas_incluidas: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    page: int = 1

    @property
    def tipo_art_fab(self) -> str:
        return tipo_art_fab_desde_param(self.tipo_producto)

    @property
    def offset(self) -> int:
        return (max(1, self.page) - 1) * PAGE_SIZE


def tipo_art_fab_desde_param(tipo_producto: Optional[str]) -> str:
    t = (tipo_producto or TIPO_PRODUCTO_TERMINADO).strip().lower()
    if t == TIPO_PRODUCTO_2DA:
        return TIPO_2DA
    return TIPO_TERMINADO


def tipo_producto_desde_art_fab(tipo_art_fab: str) -> str:
    if (tipo_art_fab or "").strip().lower() == TIPO_2DA.lower():
        return TIPO_PRODUCTO_2DA
    return TIPO_PRODUCTO_TERMINADO


def parse_listas_incluidas(raw_list: Sequence[str]) -> List[int]:
    out: List[int] = []
    for raw in raw_list:
        n = to_int_or_none(raw)
        if n in LISTAS_VALIDAS and n not in out:
            out.append(n)
    return out or [1, 2, 3, 4, 5]


def _parse_int_list(values: Sequence[str]) -> List[int]:
    out: List[int] = []
    for v in values:
        n = to_int_or_none(v)
        if n is not None and n not in out:
            out.append(n)
    return out


def parse_precios_terminados_filtros(get_params: Any) -> PreciosTerminadosFiltros:
    tipo = (get_params.get("tipo_producto") or TIPO_PRODUCTO_TERMINADO).strip().lower()
    if tipo not in (TIPO_PRODUCTO_TERMINADO, TIPO_PRODUCTO_2DA):
        tipo = TIPO_PRODUCTO_TERMINADO

    page = max(1, to_int_or_none(get_params.get("page")) or 1)

    return PreciosTerminadosFiltros(
        tipo_producto=tipo,
        marcas_incluidos=_parse_int_list(get_params.getlist("marcas_incluidos")),
        codigos_incluidos=_parse_int_list(get_params.getlist("codigos_incluidos")),
        proveedores_incluidos=_parse_int_list(get_params.getlist("proveedores_incluidos")),
        rubros_incluidos=_parse_int_list(get_params.getlist("rubros_incluidos")),
        subrubros_incluidos=_parse_int_list(get_params.getlist("subrubros_incluidos")),
        listas_incluidas=parse_listas_incluidas(get_params.getlist("listas_incluidas")),
        page=page,
    )


def build_filtros_query_string(
    filtros: PreciosTerminadosFiltros,
    *,
    page: Optional[int] = None,
    reset_secundarios: bool = False,
) -> str:
    pairs: List[Tuple[str, str]] = [("tipo_producto", filtros.tipo_producto)]
    if not reset_secundarios:
        for m in filtros.marcas_incluidos:
            pairs.append(("marcas_incluidos", str(m)))
        for c in filtros.codigos_incluidos:
            pairs.append(("codigos_incluidos", str(c)))
        for p in filtros.proveedores_incluidos:
            pairs.append(("proveedores_incluidos", str(p)))
        for r in filtros.rubros_incluidos:
            pairs.append(("rubros_incluidos", str(r)))
        for s in filtros.subrubros_incluidos:
            pairs.append(("subrubros_incluidos", str(s)))
        for li in filtros.listas_incluidas:
            if li in LISTAS_VALIDAS:
                pairs.append(("listas_incluidas", str(li)))
    else:
        for li in filtros.listas_incluidas:
            if li in LISTAS_VALIDAS:
                pairs.append(("listas_incluidas", str(li)))
    p = page if page is not None else filtros.page
    if p > 1:
        pairs.append(("page", str(p)))
    return urlencode(pairs)


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] if not isinstance(row, dict) else list(row.values())[0]) or ""
        nombre = str(nombre).strip()
        if nombre.lower() == nombre_lower:
            return nombre
    return None


def _where_base(alias: str = "a", *, tipo_producto: str = TIPO_PRODUCTO_TERMINADO) -> Tuple[str, List[Any]]:
    """
    Universo base: no discontinuos + tipo de fabricación.
    Terminado incluye vacío (legacy sin tipo_art_fab cargado) y 'Terminado'.
    """
    campo = f"LOWER(COALESCE(TRIM({alias}.tipo_art_fab), ''))"
    t = (tipo_producto or TIPO_PRODUCTO_TERMINADO).strip().lower()
    if t == TIPO_PRODUCTO_2DA:
        tipo_sql = f"{campo} = %s"
        tipo_params: List[Any] = ["fabricado 2da"]
    else:
        tipo_sql = f"{campo} IN (%s, %s)"
        tipo_params = ["terminado", ""]
    return (
        f"{tipo_sql} AND COALESCE({alias}.Discontinuo, 'No') = 'No'",
        tipo_params,
    )


def _append_filtros_where(
    filtros: PreciosTerminadosFiltros,
    alias: str = "a",
) -> Tuple[str, List[Any]]:
    parts: List[str] = []
    params: List[Any] = []

    if filtros.marcas_incluidos:
        ph = ",".join(["%s"] * len(filtros.marcas_incluidos))
        parts.append(f"{alias}.CodigoMarca IN ({ph})")
        params.extend(filtros.marcas_incluidos)

    if filtros.codigos_incluidos:
        ph = ",".join(["%s"] * len(filtros.codigos_incluidos))
        parts.append(f"{alias}.IDArt IN ({ph})")
        params.extend(filtros.codigos_incluidos)

    if filtros.proveedores_incluidos:
        ph = ",".join(["%s"] * len(filtros.proveedores_incluidos))
        parts.append(f"{alias}.CodigoProveedor IN ({ph})")
        params.extend(filtros.proveedores_incluidos)

    if filtros.rubros_incluidos:
        ph = ",".join(["%s"] * len(filtros.rubros_incluidos))
        parts.append(f"{alias}.CodigoRubro IN ({ph})")
        params.extend(filtros.rubros_incluidos)

    if filtros.subrubros_incluidos:
        ph = ",".join(["%s"] * len(filtros.subrubros_incluidos))
        parts.append(f"{alias}.IDSubRubro IN ({ph})")
        params.extend(filtros.subrubros_incluidos)

    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def _sql_universo_from(
    tbl_art: str,
    *,
    join_marca: bool = False,
    join_proveedor: bool = False,
    join_rubro: bool = False,
    join_subrubro: bool = False,
) -> str:
    tart = tbl_art.replace("`", "``")
    joins = ""
    if join_marca:
        joins += " INNER JOIN marca m ON m.CodMarca = a.CodigoMarca"
    if join_proveedor:
        joins += " INNER JOIN proveedor p ON p.Codigo = a.CodigoProveedor"
    if join_rubro:
        joins += " INNER JOIN rubro r ON r.CodigoRubro = a.CodigoRubro"
    if join_subrubro:
        joins += " INNER JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro"
    return f"FROM `{tart}` a{joins}"


def listar_marcas_catalogo_precios(
    base_empresa: str,
    tipo_producto: str,
) -> List[Dict[str, Any]]:
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []
            base, base_params = _where_base(tipo_producto=tipo_producto)
            sql_from = _sql_universo_from(tbl_art, join_marca=True)
            cursor.execute(
                f"""
                SELECT DISTINCT m.CodMarca AS value, COALESCE(m.NombreMarca, '') AS label
                {sql_from}
                WHERE {base}
                ORDER BY label
                """,
                base_params,
            )
            return [
                {"value": int(r["value"]), "label": str_or_default(r.get("label"), "-")}
                for r in cursor.fetchall()
                if r.get("value") is not None
            ]
    except Exception as exc:
        logger.warning("listar_marcas_catalogo_precios %s: %s", base_empresa, exc)
        return []


def listar_proveedores_catalogo_precios(
    base_empresa: str,
    tipo_producto: str,
) -> List[Dict[str, Any]]:
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []
            base, base_params = _where_base(tipo_producto=tipo_producto)
            sql_from = _sql_universo_from(tbl_art, join_proveedor=True)
            cursor.execute(
                f"""
                SELECT DISTINCT p.Codigo AS value, COALESCE(p.Nombre, '') AS label
                {sql_from}
                WHERE {base} AND p.Codigo <> 1
                ORDER BY label
                """,
                base_params,
            )
            return [
                {"value": int(r["value"]), "label": str_or_default(r.get("label"), "-")}
                for r in cursor.fetchall()
                if r.get("value") is not None
            ]
    except Exception as exc:
        logger.warning("listar_proveedores_catalogo_precios %s: %s", base_empresa, exc)
        return []


def listar_rubros_catalogo_precios(
    base_empresa: str,
    tipo_producto: str,
) -> List[Dict[str, Any]]:
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []
            base, base_params = _where_base(tipo_producto=tipo_producto)
            sql_from = _sql_universo_from(tbl_art, join_rubro=True)
            cursor.execute(
                f"""
                SELECT DISTINCT r.CodigoRubro AS value, COALESCE(r.NombreRubro, '') AS label
                {sql_from}
                WHERE {base}
                ORDER BY label
                """,
                base_params,
            )
            return [
                {"value": int(r["value"]), "label": str_or_default(r.get("label"), "-")}
                for r in cursor.fetchall()
                if r.get("value") is not None
            ]
    except Exception as exc:
        logger.warning("listar_rubros_catalogo_precios %s: %s", base_empresa, exc)
        return []


def listar_subrubros_catalogo_precios(
    base_empresa: str,
    tipo_producto: str,
    *,
    rubros_incluidos: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []
            base, base_params = _where_base(tipo_producto=tipo_producto)
            extra = ""
            extra_params: List[Any] = []
            if rubros_incluidos:
                ph = ",".join(["%s"] * len(rubros_incluidos))
                extra = f" AND a.CodigoRubro IN ({ph})"
                extra_params = list(rubros_incluidos)
            sql_from = _sql_universo_from(tbl_art, join_subrubro=True)
            cursor.execute(
                f"""
                SELECT DISTINCT sr.IDSubRubro AS value,
                       COALESCE(sr.NombreSubRubro, '') AS label,
                       sr.CodigoRubro AS codigo_rubro
                {sql_from}
                WHERE {base}{extra}
                ORDER BY label
                """,
                base_params + extra_params,
            )
            return [
                {
                    "value": int(r["value"]),
                    "label": str_or_default(r.get("label"), "-"),
                    "codigo_rubro": to_int_or_none(r.get("codigo_rubro")),
                }
                for r in cursor.fetchall()
                if r.get("value") is not None
            ]
    except Exception as exc:
        logger.warning("listar_subrubros_catalogo_precios %s: %s", base_empresa, exc)
        return []


def _etiqueta_articulo_unico(id_articulo: Any, id_manual: Any, nombre: Any) -> str:
    """Etiqueta por IDArt (único); id_manual puede repetirse entre artículos."""
    manual = str_codigo_manual_articulo(id_manual)
    nom = str_or_default(nombre, "-")
    aid = to_int_or_none(id_articulo)
    if aid is not None:
        return f"ID {aid} · {manual} — {nom}"
    return f"{manual} — {nom}"


def buscar_articulos_codigo_precios(
    base_empresa: str,
    q: str,
    tipo_producto: str,
    *,
    excluir_ids: Optional[Sequence[int]] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    q = (q or "").strip()
    if len(q) < _BUSQUEDA_MIN_LEN:
        return []
    limit = min(max(1, limit), 50)
    like = f"%{q}%"
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []
            base, base_params = _where_base(tipo_producto=tipo_producto)
            extra = ""
            extra_params: List[Any] = []
            if excluir_ids:
                ph = ",".join(["%s"] * len(excluir_ids))
                extra = f" AND a.IDArt NOT IN ({ph})"
                extra_params = list(excluir_ids)
            tart = tbl_art.replace("`", "``")
            cursor.execute(
                f"""
                SELECT a.IDArt AS id_articulo, a.id_manual, a.NombreArticulo AS nombre
                FROM `{tart}` a
                WHERE {base}
                  AND (
                    a.id_manual LIKE %s OR a.NombreArticulo LIKE %s
                    OR CAST(a.IDArt AS CHAR) LIKE %s
                  ){extra}
                ORDER BY a.id_manual
                LIMIT %s
                """,
                base_params + [like, like, like] + extra_params + [limit],
            )
            out: List[Dict[str, Any]] = []
            for r in cursor.fetchall():
                manual = str_codigo_manual_articulo(r.get("id_manual"))
                nombre = str_or_default(r.get("nombre"), "-")
                out.append(
                    {
                        "id_articulo": to_int_or_none(r.get("id_articulo")),
                        "id_manual": manual,
                        "nombre": nombre,
                        "codigo_display": _etiqueta_articulo_unico(
                            r.get("id_articulo"), r.get("id_manual"), r.get("nombre")
                        ),
                    }
                )
            return out
    except Exception as exc:
        logger.warning("buscar_articulos_codigo_precios %s: %s", base_empresa, exc)
        return []


def resolver_articulos_seleccionados(
    base_empresa: str,
    ids: Sequence[int],
    tipo_producto: str,
) -> List[Dict[str, Any]]:
    if not ids:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []
            ph = ",".join(["%s"] * len(ids))
            tart = tbl_art.replace("`", "``")
            base, base_params = _where_base(tipo_producto=tipo_producto)
            cursor.execute(
                f"""
                SELECT a.IDArt AS id_articulo, a.id_manual, a.NombreArticulo AS nombre
                FROM `{tart}` a
                WHERE a.IDArt IN ({ph}) AND {base}
                """,
                list(ids) + base_params,
            )
            out = []
            for r in cursor.fetchall():
                manual = str_codigo_manual_articulo(r.get("id_manual"))
                nombre = str_or_default(r.get("nombre"), "-")
                out.append(
                    {
                        "id_articulo": to_int_or_none(r.get("id_articulo")),
                        "id_manual": manual,
                        "nombre": nombre,
                        "codigo_display": _etiqueta_articulo_unico(
                            r.get("id_articulo"), r.get("id_manual"), r.get("nombre")
                        ),
                    }
                )
            return out
    except Exception as exc:
        logger.warning("resolver_articulos_seleccionados %s: %s", base_empresa, exc)
        return []


def _row_a_fila(row: Dict[str, Any], listas: Sequence[int]) -> Dict[str, Any]:
    manual = str_codigo_manual_articulo(row.get("id_manual"))
    alic = Decimal(str(row.get("alicuota_iva") or 21))
    imp = Decimal(str(row.get("impuesto_interno") or 0))
    precios_por_lista: List[Dict[str, Any]] = []
    for lista in listas:
        neto = to_decimal_or_none(row.get(f"precio{lista}_neto"))
        final = to_decimal_or_none(row.get(f"precio{lista}_final"))
        precios_por_lista.append(
            {
                "lista": lista,
                "neto": float(neto) if neto is not None else 0.0,
                "final": float(final) if final is not None else 0.0,
            }
        )
    reserva = to_decimal_or_none(row.get("stock_reserva")) or Decimal("0")
    return {
        "id_articulo": to_int_or_none(row.get("IDArt")),
        "id_manual": manual,
        "nombre_articulo": str_or_default(row.get("NombreArticulo"), "-"),
        "stock_reserva": float(reserva),
        "alicuota_iva": float(alic),
        "impuesto_interno": float(imp),
        "promocion": str_or_default(row.get("promocion"), "No"),
        "precios_por_lista": precios_por_lista,
    }


def listar_precios_terminados(
    base_empresa: str,
    filtros: PreciosTerminadosFiltros,
) -> Dict[str, Any]:
    listas = [li for li in filtros.listas_incluidas if li in LISTAS_VALIDAS] or [1, 2, 3, 4, 5]
    cols_precio = []
    for i in range(1, 6):
        cols_precio.append(f"a.Precio{i}V AS precio{i}_neto")
        cols_precio.append(f"a.Precio{i}VI AS precio{i}_final")
    cols_sql = ", ".join(
        [
            "a.IDArt",
            "a.id_manual",
            "a.NombreArticulo",
            "a.stock_reserva",
            "a.impuesto_interno",
            "a.promocion",
            "COALESCE(i.Alicuota, 21) AS alicuota_iva",
        ]
        + cols_precio
    )
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return {"filas": [], "total_count": 0, "total_pages": 0}
            base, base_params = _where_base(tipo_producto=filtros.tipo_producto)
            extra_where, extra_params = _append_filtros_where(filtros)
            tart = tbl_art.replace("`", "``")
            where_full = base + extra_where
            params_count = base_params + extra_params

            cursor.execute(
                f"SELECT COUNT(*) AS cnt FROM `{tart}` a WHERE {where_full}",
                tuple(params_count),
            )
            total = int((cursor.fetchone() or {}).get("cnt") or 0)
            total_pages = max(1, math.ceil(total / PAGE_SIZE)) if total else 0

            cursor.execute(
                f"""
                SELECT {cols_sql}
                FROM `{tart}` a
                LEFT JOIN iva i ON i.ID = a.Alicuota
                WHERE {where_full}
                ORDER BY a.id_manual
                LIMIT %s OFFSET %s
                """,
                tuple(params_count) + (PAGE_SIZE, filtros.offset),
            )
            filas = [_row_a_fila(dict(r), listas) for r in cursor.fetchall()]
            return {
                "filas": filas,
                "total_count": total,
                "total_pages": total_pages,
                "page": filtros.page,
                "page_size": PAGE_SIZE,
            }
    except Exception as exc:
        logger.warning("listar_precios_terminados %s: %s", base_empresa, exc, exc_info=True)
        return {"filas": [], "total_count": 0, "total_pages": 0, "error": str(exc)}


def contar_universo_filtrado(base_empresa: str, filtros: PreciosTerminadosFiltros) -> int:
    res = listar_precios_terminados(base_empresa, PreciosTerminadosFiltros(
        tipo_producto=filtros.tipo_producto,
        marcas_incluidos=filtros.marcas_incluidos,
        codigos_incluidos=filtros.codigos_incluidos,
        proveedores_incluidos=filtros.proveedores_incluidos,
        rubros_incluidos=filtros.rubros_incluidos,
        subrubros_incluidos=filtros.subrubros_incluidos,
        listas_incluidas=filtros.listas_incluidas,
        page=1,
    ))
    return int(res.get("total_count") or 0)


def _iter_ids_filtrados(
    base_empresa: str,
    filtros: PreciosTerminadosFiltros,
    ids_articulos: Optional[Sequence[int]] = None,
):
    ids: List[int] = []
    if ids_articulos is not None:
        for raw in ids_articulos:
            n = to_int_or_none(raw)
            if n is not None and n not in ids:
                ids.append(n)
        if not ids:
            return
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return
            base, base_params = _where_base(tipo_producto=filtros.tipo_producto)
            extra_where, extra_params = _append_filtros_where(filtros)
            tart = tbl_art.replace("`", "``")
            where_full = base + extra_where
            params: List[Any] = list(base_params) + list(extra_params)
            if ids:
                ph = ",".join(["%s"] * len(ids))
                where_full += f" AND a.IDArt IN ({ph})"
                params.extend(ids)
            cursor.execute(
                f"""
                SELECT a.IDArt,
                       a.PrecioCosto, a.impuesto_interno,
                       COALESCE(i.Alicuota, 21) AS alicuota_iva,
                       a.Precio1V, a.Precio2V, a.Precio3V, a.Precio4V, a.Precio5V,
                       a.Precio1VI, a.Precio2VI, a.Precio3VI, a.Precio4VI, a.Precio5VI,
                       a.stock_reserva
                FROM `{tart}` a
                LEFT JOIN iva i ON i.ID = a.Alicuota
                WHERE {where_full}
                ORDER BY a.IDArt
                """,
                tuple(params),
            )
            for row in cursor.fetchall():
                yield dict(row)
    except Exception as exc:
        logger.warning("_iter_ids_filtrados %s: %s", base_empresa, exc, exc_info=True)


def _aplicar_operacion_valor(
    valor: Decimal,
    operacion: str,
    parametro: Decimal,
) -> Decimal:
    op = (operacion or "").strip().lower()
    if op in ("porcentaje_mas", "pct_mas", "+%"):
        return q2(valor * (Decimal("1") + parametro / Decimal("100")))
    if op in ("porcentaje_menos", "pct_menos", "-%"):
        return q2(valor * (Decimal("1") - parametro / Decimal("100")))
    if op in ("sumar", "monto_mas", "+"):
        return q2(valor + parametro)
    if op in ("restar", "monto_menos", "-"):
        return q2(valor - parametro)
    if op in ("establecer", "set", "="):
        return q2(parametro)
    if op in ("redondear", "round"):
        # parametro = decimales (0, 1, 2) o múltiplo (10, 100)
        if parametro >= 1 and parametro == parametro.to_integral_value():
            mult = parametro
            if mult > 0:
                return q2((valor / mult).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * mult)
        dec = int(parametro) if parametro <= 4 else 2
        quant = Decimal("1") if dec == 0 else Decimal("0.1") if dec == 1 else Q2
        return valor.quantize(quant, rounding=ROUND_HALF_UP)
    return valor


def preview_cambio_masivo(
    base_empresa: str,
    filtros: PreciosTerminadosFiltros,
    operacion: Dict[str, Any],
    *,
    ids_articulos: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    ambito = (operacion.get("ambito") or "").strip().lower()
    listas_op = _listas_operacion_masivo(operacion, filtros)
    if ambito in ("precio_neto", "neto", "precio_final", "final") and not listas_op:
        return {
            "ok": False,
            "error": "listas_requeridas",
            "total_articulos": 0,
            "operacion": operacion,
            "tipo_producto": filtros.tipo_producto,
        }

    if ids_articulos is not None:
        ids = [to_int_or_none(x) for x in ids_articulos]
        ids = [x for x in ids if x is not None]
        total = len(ids)
    else:
        total = contar_universo_filtrado(base_empresa, filtros)

    return {
        "ok": True,
        "total_articulos": total,
        "operacion": operacion,
        "tipo_producto": filtros.tipo_producto,
        "alcance": "tabla_visible" if ids_articulos is not None else "universo_filtrado",
    }


def _listas_operacion_masivo(
    operacion: Dict[str, Any],
    filtros: PreciosTerminadosFiltros,
) -> List[int]:
    listas_op = [to_int_or_none(x) for x in (operacion.get("listas") or [])]
    return [x for x in listas_op if x in LISTAS_VALIDAS]


def aplicar_cambio_masivo(
    base_empresa: str,
    filtros: PreciosTerminadosFiltros,
    operacion: Dict[str, Any],
    *,
    id_usuario: Optional[int] = None,
    ids_articulos: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """
    operacion: {
      ambito: precio_neto | precio_final | reserva,
      listas: [1,2,...]  (si ambito es precio),
      tipo_operacion: porcentaje_mas | porcentaje_menos | sumar | restar | establecer | redondear,
      valor: number
    }
    """
    ambito = (operacion.get("ambito") or "").strip().lower()
    tipo_op = (operacion.get("tipo_operacion") or "").strip().lower()
    valor_param = Decimal(str(operacion.get("valor") or 0))
    listas_op = _listas_operacion_masivo(operacion, filtros)

    if ambito in ("precio_neto", "neto", "precio_final", "final") and not listas_op:
        return {"ok": False, "error": "listas_requeridas"}

    if ids_articulos is not None:
        ids = [to_int_or_none(x) for x in ids_articulos]
        ids = [x for x in ids if x is not None]
        if not ids:
            return {"ok": False, "error": "sin_articulos_visibles", "actualizados": 0, "errores": []}

    actualizados = 0
    errores: List[Dict[str, Any]] = []

    for row in _iter_ids_filtrados(base_empresa, filtros, ids_articulos=ids_articulos):
        aid = to_int_or_none(row.get("IDArt"))
        if aid is None:
            continue
        alic = Decimal(str(row.get("alicuota_iva") or 21))
        imp = Decimal(str(row.get("impuesto_interno") or 0))
        cambios: Dict[str, Any] = {"precios": {}}

        if ambito == "reserva":
            actual = Decimal(str(row.get("stock_reserva") or 0))
            nuevo = _aplicar_operacion_valor(actual, tipo_op, valor_param)
            if nuevo < 0:
                nuevo = Decimal("0")
            cambios["stock_reserva"] = float(nuevo)
        elif ambito in ("precio_neto", "neto"):
            for lista in listas_op:
                col = f"Precio{lista}V"
                actual = Decimal(str(row.get(col) or 0))
                neto = _aplicar_operacion_valor(actual, tipo_op, valor_param)
                if neto < 0:
                    neto = Decimal("0")
                final = calcular_final_desde_neto(
                    neto, alicuota_iva=alic, impuesto_interno_pct=imp
                )
                cambios["precios"][lista] = {"neto": float(neto), "final": float(final)}
        elif ambito in ("precio_final", "final"):
            for lista in listas_op:
                col = f"Precio{lista}VI"
                actual = Decimal(str(row.get(col) or 0))
                final = _aplicar_operacion_valor(actual, tipo_op, valor_param)
                if final < 0:
                    final = Decimal("0")
                neto = calcular_neto_desde_final(
                    final, alicuota_iva=alic, impuesto_interno_pct=imp
                )
                cambios["precios"][lista] = {"neto": float(neto), "final": float(final)}
        else:
            return {"ok": False, "error": "ambito_invalido"}

        if not cambios.get("precios") and "stock_reserva" not in cambios:
            continue

        res = aplicar_cambios_articulo(
            base_empresa, aid, cambios, id_usuario=id_usuario
        )
        if res.get("ok") and res.get("actualizado"):
            actualizados += 1
        elif not res.get("ok"):
            errores.append({"id_articulo": aid, "error": res.get("error")})

    return {
        "ok": len(errores) == 0,
        "actualizados": actualizados,
        "errores": errores,
    }


def nombres_listas_precio() -> Dict[int, str]:
    return {
        1: "Lista 1",
        2: "Lista 2",
        3: "Lista 3",
        4: "Lista 4",
        5: "Lista 5",
    }


__all__ = [
    "PAGE_SIZE",
    "TIPO_PRODUCTO_2DA",
    "TIPO_PRODUCTO_TERMINADO",
    "PreciosTerminadosFiltros",
    "aplicar_cambio_masivo",
    "build_filtros_query_string",
    "buscar_articulos_codigo_precios",
    "guardar_lote",
    "listar_marcas_catalogo_precios",
    "listar_precios_terminados",
    "listar_proveedores_catalogo_precios",
    "listar_rubros_catalogo_precios",
    "listar_subrubros_catalogo_precios",
    "nombres_listas_precio",
    "parse_precios_terminados_filtros",
    "preview_cambio_masivo",
    "resolver_articulos_seleccionados",
    "tipo_art_fab_desde_param",
]
