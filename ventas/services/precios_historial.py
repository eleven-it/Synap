# -*- coding: utf-8 -*-
"""Consulta y analítica de precios_historial (MySQL legacy)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import (
    str_codigo_manual_articulo,
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)

from ventas.services.precios_articulo_legacy import LISTAS_VALIDAS

logger = logging.getLogger(__name__)

Q2 = Decimal("0.01")
_RANKING_LIMIT_DEFAULT = 50
_HISTORIAL_LIMIT_DEFAULT = 200


@dataclass
class HistorialPreciosFiltros:
    lista: int = 1
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    rubros_incluidos: List[int] = field(default_factory=list)
    marcas_incluidos: List[int] = field(default_factory=list)
    proveedores_incluidos: List[int] = field(default_factory=list)
    solo_synap: bool = False
    tipo_modificacion: Optional[str] = None
    limit: int = _RANKING_LIMIT_DEFAULT


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] if not isinstance(row, dict) else list(row.values())[0]) or ""
        nombre = str(nombre).strip()
        if nombre.lower() == nombre_lower:
            return nombre
    return None


def _cols_lista(lista: int) -> Tuple[str, str, str]:
    li = lista if lista in LISTAS_VALIDAS else 1
    return f"precio_neto{li}", f"precio_iva{li}", f"util{li}"


def _q2(d: Optional[Decimal]) -> Optional[float]:
    if d is None:
        return None
    return float(d.quantize(Q2))


def _delta_pct(actual: Optional[Decimal], anterior: Optional[Decimal]) -> Optional[float]:
    if actual is None or anterior is None:
        return None
    if anterior == 0:
        return None
    return float(((actual - anterior) / anterior * Decimal("100")).quantize(Q2))


def _parse_fecha_default(
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
) -> Tuple[date, date]:
    hoy = date.today()
    hasta = fecha_hasta or hoy
    desde = fecha_desde or (hasta - timedelta(days=90))
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def _enriquecer_filas_con_deltas(
    filas_raw: List[Dict[str, Any]],
    lista: int,
) -> List[Dict[str, Any]]:
    col_neto, col_final, col_util = _cols_lista(lista)
    out: List[Dict[str, Any]] = []
    prev_neto: Optional[Decimal] = None
    prev_final: Optional[Decimal] = None
    prev_costo: Optional[Decimal] = None
    prev_fecha: Optional[date] = None

    for r in filas_raw:
        neto = to_decimal_or_none(r.get(col_neto))
        final = to_decimal_or_none(r.get(col_final))
        util = to_decimal_or_none(r.get(col_util))
        costo = to_decimal_or_none(r.get("precio_costo"))
        f = r.get("fecha")
        if isinstance(f, datetime):
            f = f.date()
        dias_desde = None
        if prev_fecha and f:
            dias_desde = (f - prev_fecha).days

        delta_neto = None
        delta_pct = None
        if neto is not None and prev_neto is not None:
            delta_neto = _q2(neto - prev_neto)
            delta_pct = _delta_pct(neto, prev_neto)

        item = {
            "id_precios_historial": to_int_or_none(r.get("id_precios_historial")),
            "fecha": f.isoformat() if f else None,
            "fecha_control": str(r.get("fecha_control") or ""),
            "tipo_modificacion": str_or_default(r.get("tipo_modificacion"), "-"),
            "id_usuario": to_int_or_none(r.get("id_usuario")),
            "lista": lista,
            "neto": _q2(neto),
            "final": _q2(final),
            "util": _q2(util),
            "precio_costo": _q2(costo),
            "alicuota_iva": _q2(to_decimal_or_none(r.get("alicuota_iva"))),
            "delta_neto": delta_neto,
            "delta_pct": delta_pct,
            "delta_costo": _q2(costo - prev_costo) if costo is not None and prev_costo is not None else None,
            "dias_desde_anterior": dias_desde,
            "nombre_articulo": str_or_default(r.get("nombre_articulo"), "-"),
        }
        out.append(item)
        prev_neto = neto if neto is not None else prev_neto
        prev_final = final if final is not None else prev_final
        prev_costo = costo if costo is not None else prev_costo
        if f:
            prev_fecha = f

    return out


def listar_historial_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    lista: int = 1,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    limit: int = _HISTORIAL_LIMIT_DEFAULT,
) -> Dict[str, Any]:
    """Serie temporal de snapshots para un artículo."""
    lista = lista if lista in LISTAS_VALIDAS else 1
    desde, hasta = _parse_fecha_default(fecha_desde, fecha_hasta)
    limit = min(max(1, limit), 500)
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "precios_historial")
            if not tbl:
                return {"filas": [], "resumen": {}, "error": "tabla_no_encontrada"}
            th = tbl.replace("`", "``")
            cursor.execute(
                f"""
                SELECT id_precios_historial, fecha, fecha_control, tipo_modificacion,
                       id_usuario, nombre_articulo, precio_costo, alicuota_iva,
                       precio_neto1, precio_neto2, precio_neto3, precio_neto4, precio_neto5,
                       precio_iva1, precio_iva2, precio_iva3, precio_iva4, precio_iva5,
                       util1, util2, util3, util4, util5
                FROM `{th}`
                WHERE id_articulo = %s
                  AND fecha >= %s AND fecha <= %s
                ORDER BY fecha_control ASC, id_precios_historial ASC
                LIMIT %s
                """,
                (id_articulo, desde, hasta, limit),
            )
            raw = [dict(r) for r in cursor.fetchall()]
            filas = _enriquecer_filas_con_deltas(raw, lista)
            resumen = resumen_evolucion_desde_filas(filas, lista)
            return {
                "id_articulo": id_articulo,
                "lista": lista,
                "fecha_desde": desde.isoformat(),
                "fecha_hasta": hasta.isoformat(),
                "filas": filas,
                "resumen": resumen,
            }
    except Exception as exc:
        logger.warning("listar_historial_articulo %s id=%s: %s", base_empresa, id_articulo, exc)
        return {"filas": [], "resumen": {}, "error": str(exc)}


def resumen_evolucion_desde_filas(
    filas: Sequence[Dict[str, Any]],
    lista: int,
) -> Dict[str, Any]:
    if not filas:
        return {
            "lista": lista,
            "cantidad_cambios": 0,
            "neto_inicial": None,
            "neto_final": None,
            "variacion_pct_acumulada": None,
        }
    netos = [f["neto"] for f in filas if f.get("neto") is not None]
    inicial = netos[0] if netos else None
    final = netos[-1] if netos else None
    var_pct = None
    if inicial is not None and final is not None and inicial != 0:
        var_pct = round((final - inicial) / inicial * 100, 2)
    return {
        "lista": lista,
        "cantidad_cambios": len(filas),
        "neto_inicial": inicial,
        "neto_final": final,
        "final_inicial": filas[0].get("final"),
        "final_final": filas[-1].get("final"),
        "variacion_pct_acumulada": var_pct,
    }


def _where_ranking(filtros: HistorialPreciosFiltros, alias_hist: str = "h", alias_art: str = "a") -> Tuple[str, List[Any]]:
    desde, hasta = _parse_fecha_default(filtros.fecha_desde, filtros.fecha_hasta)
    parts = [
        f"{alias_hist}.fecha >= %s",
        f"{alias_hist}.fecha <= %s",
    ]
    params: List[Any] = [desde, hasta]
    if filtros.rubros_incluidos:
        ph = ",".join(["%s"] * len(filtros.rubros_incluidos))
        parts.append(f"{alias_art}.CodigoRubro IN ({ph})")
        params.extend(filtros.rubros_incluidos)
    if filtros.marcas_incluidos:
        ph = ",".join(["%s"] * len(filtros.marcas_incluidos))
        parts.append(f"{alias_art}.CodigoMarca IN ({ph})")
        params.extend(filtros.marcas_incluidos)
    if filtros.proveedores_incluidos:
        ph = ",".join(["%s"] * len(filtros.proveedores_incluidos))
        parts.append(f"{alias_art}.CodigoProveedor IN ({ph})")
        params.extend(filtros.proveedores_incluidos)
    if filtros.solo_synap:
        parts.append(f"{alias_hist}.tipo_modificacion LIKE %s")
        params.append("Synap%")
    if filtros.tipo_modificacion:
        parts.append(f"{alias_hist}.tipo_modificacion = %s")
        params.append(filtros.tipo_modificacion.strip())
    return " AND ".join(parts), params


def ranking_variaciones_precios(
    base_empresa: str,
    filtros: HistorialPreciosFiltros,
) -> Dict[str, Any]:
    """
    Ranking de artículos por variación % de precio neto en el período
    (primer vs último snapshot en rango).
    """
    lista = filtros.lista if filtros.lista in LISTAS_VALIDAS else 1
    col_neto, col_final, col_util = _cols_lista(lista)
    desde, hasta = _parse_fecha_default(filtros.fecha_desde, filtros.fecha_hasta)
    limit = min(max(1, filtros.limit), 200)

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_h = _nombre_tabla(cursor, "precios_historial")
            tbl_a = _nombre_tabla(cursor, "articulo")
            tbl_r = _nombre_tabla(cursor, "rubro")
            tbl_m = _nombre_tabla(cursor, "marca")
            if not tbl_h or not tbl_a:
                return {"filas": [], "totals": {}, "error": "tabla_no_encontrada"}

            th = tbl_h.replace("`", "``")
            ta = tbl_a.replace("`", "``")
            join_rubro = ""
            join_marca = ""
            sel_rubro = "NULL AS nombre_rubro"
            sel_marca = "NULL AS nombre_marca"
            if tbl_r:
                tr = tbl_r.replace("`", "``")
                join_rubro = f" LEFT JOIN `{tr}` r ON r.CodigoRubro = a.CodigoRubro"
                sel_rubro = "COALESCE(r.NombreRubro, '') AS nombre_rubro"
            if tbl_m:
                tm = tbl_m.replace("`", "``")
                join_marca = f" LEFT JOIN `{tm}` m ON m.CodMarca = a.CodigoMarca"
                sel_marca = "COALESCE(m.NombreMarca, '') AS nombre_marca"

            where_sql, params = _where_ranking(filtros)
            cursor.execute(
                f"""
                SELECT h.id_articulo, h.fecha, h.fecha_control, h.id_precios_historial,
                       h.{col_neto} AS neto, h.{col_final} AS final, h.{col_util} AS util,
                       h.precio_costo, h.tipo_modificacion,
                       a.id_manual, a.NombreArticulo AS nombre_articulo,
                       {sel_rubro}, {sel_marca}
                FROM `{th}` h
                INNER JOIN `{ta}` a ON a.IDArt = h.id_articulo
                {join_rubro}{join_marca}
                WHERE {where_sql}
                ORDER BY h.id_articulo, h.fecha_control ASC, h.id_precios_historial ASC
                """,
                tuple(params),
            )
            rows = cursor.fetchall()

        por_art: Dict[int, List[Dict[str, Any]]] = {}
        meta_art: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            aid = to_int_or_none(r.get("id_articulo"))
            if aid is None:
                continue
            por_art.setdefault(aid, []).append(dict(r))
            if aid not in meta_art:
                meta_art[aid] = {
                    "id_articulo": aid,
                    "id_manual": str_codigo_manual_articulo(r.get("id_manual")),
                    "nombre_articulo": str_or_default(r.get("nombre_articulo"), "-"),
                    "nombre_rubro": str_or_default(r.get("nombre_rubro"), "-"),
                    "nombre_marca": str_or_default(r.get("nombre_marca"), "-"),
                }

        ranking: List[Dict[str, Any]] = []
        for aid, snaps in por_art.items():
            if len(snaps) < 1:
                continue
            first = snaps[0]
            last = snaps[-1]
            neto_ini = to_decimal_or_none(first.get("neto"))
            neto_fin = to_decimal_or_none(last.get("neto"))
            if neto_ini is None or neto_fin is None:
                continue
            var_pct = _delta_pct(neto_fin, neto_ini)
            if var_pct is None and neto_ini == neto_fin:
                var_pct = 0.0
            if var_pct is None:
                continue
            m = meta_art[aid]
            ranking.append(
                {
                    **m,
                    "lista": lista,
                    "neto_inicial": _q2(neto_ini),
                    "neto_final": _q2(neto_fin),
                    "variacion_pct": var_pct,
                    "cantidad_registros": len(snaps),
                    "ultimo_tipo_modificacion": str_or_default(last.get("tipo_modificacion"), "-"),
                }
            )

        ranking.sort(key=lambda x: x.get("variacion_pct") or 0, reverse=True)
        ranking = ranking[:limit]
        deltas = [r["variacion_pct"] for r in ranking if r.get("variacion_pct") is not None]
        promedio = round(sum(deltas) / len(deltas), 2) if deltas else 0.0

        return {
            "filas": ranking,
            "fecha_desde": desde.isoformat(),
            "fecha_hasta": hasta.isoformat(),
            "lista": lista,
            "totals": {
                "articulos_ranking": len(ranking),
                "variacion_pct_promedio": promedio,
            },
        }
    except Exception as exc:
        logger.warning("ranking_variaciones_precios %s: %s", base_empresa, exc, exc_info=True)
        return {"filas": [], "totals": {}, "error": str(exc)}


def parse_historial_filtros(get_params: Any) -> HistorialPreciosFiltros:
    lista = to_int_or_none(get_params.get("lista")) or 1
    if lista not in LISTAS_VALIDAS:
        lista = 1
    fd = to_date_or_none(get_params.get("fecha_desde"))
    fh = to_date_or_none(get_params.get("fecha_hasta"))
    solo_synap = (get_params.get("solo_synap") or "").strip() in ("1", "true", "si", "sí")
    tipo = (get_params.get("tipo_modificacion") or "").strip() or None
    limit = to_int_or_none(get_params.get("limit")) or _RANKING_LIMIT_DEFAULT

    def _ints(key: str) -> List[int]:
        raw = get_params.getlist(key) if hasattr(get_params, "getlist") else []
        if not raw and get_params.get(key):
            raw = [get_params.get(key)]
        out: List[int] = []
        for v in raw:
            n = to_int_or_none(v)
            if n is not None and n not in out:
                out.append(n)
        return out

    return HistorialPreciosFiltros(
        lista=lista,
        fecha_desde=fd,
        fecha_hasta=fh,
        rubros_incluidos=_ints("rubros_incluidos"),
        marcas_incluidos=_ints("marcas_incluidos"),
        proveedores_incluidos=_ints("proveedores_incluidos"),
        solo_synap=solo_synap,
        tipo_modificacion=tipo,
        limit=limit,
    )
