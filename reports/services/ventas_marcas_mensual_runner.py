# -*- coding: utf-8 -*-
"""
Informe Ventas marcas mensual: matriz Ven → Cliente × AñoMes.

Ver SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md y MAPEO_PUW_PUM_ADMINISTRANET.md.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from django.conf import settings

from core.utils.administranet_types import str_or_default, to_date_or_none, to_decimal_or_none, to_int_or_none
from reports.models import ReportDefinition
from reports.services.connection_pool import get_mysql_pool
from reports.services.ajustes_sin_mercaderia import (
    CODIGO_SINTETICO_AJUSTES,
    NOMBRE_AJUSTES,
    NOTA_AJUSTES_INCLUIDOS,
    NOTA_AJUSTES_OMITIDOS_CATALOGO,
    consultar_ajustes_sin_mercaderia,
    filtros_catalogo_restringen,
    pin_ajustes_al_final,
)
from reports.services.articulo_venta_sql import sql_solo_tipo_art_articulo
from reports.services.query_runner import QueryResult, QueryRunnerService
from reports.services.ventas_objetivos_bo_runner import (
    _parse_int_list,
    _sql_in_viajantes,
    _vo_sql_filtros_articulo,
)
from ventas.services.objetivos_mysql import alcance_objetivos_cod_viajante, ctx_desde_runner

logger = logging.getLogger(__name__)

_MAX_MESES = 24
_TC_FALLBACK = Decimal("14.5817")
_TASA_REGALIA_DEFAULT = 0.13
_COEF_PROYECCION_DEFAULT = 1.07

from reports.services.ventas_marcas_mensual_rules import (
    FACTOR_DOCENAS_MAP as _FACTOR_DOCENAS_MAP,
    STOCK_TIPO_COMP as _STOCK_TIPO_COMP,
    TIPOS_FAC as _TIPOS_FAC,
    TIPOS_NC as _TIPOS_NC,
    factor_docenas_unimed,
    sql_base_where_clauses,
    sql_comprobantes_in_clause,
    sql_factor_docenas_expr as _sql_factor_docenas_expr,
    sql_signo_imp_post_pie_expr,
    sql_signo_qty_expr,
)


def _parse_str_list(raw: Any) -> List[str]:
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    elif not isinstance(raw, list):
        raw = []
    out: List[str] = []
    for item in raw:
        s = str_or_default(item, "").strip()
        if s:
            out.append(s)
    return out


def _norm_yyyy_mm_dd(raw: Any) -> str:
    fecha_normalizada = to_date_or_none(raw)
    if fecha_normalizada is None:
        return str_or_default(raw, "").strip()[:10]
    # to_date_or_none normaliza DATE al contrato AdministraNET: str YYYY-MM-DD.
    # No usar isoformat(): los filtros del dashboard llegan como strings.
    return fecha_normalizada


def ceil_proy_unidades(u: float, coef: float) -> float:
    """Proyección de unidades: CEILING(u × coef)."""
    return float(math.ceil(float(u) * float(coef)))


def round_proy_facturacion(f: float, coef: float) -> float:
    """Proyección de facturación: round(f × coef, 2)."""
    val = to_decimal_or_none(float(f) * float(coef), quantize="0.01")
    return float(val) if val is not None else 0.0


def _proyectar_celda(celda: Dict[str, float], coef: float) -> None:
    u = float(celda.get("u") or 0)
    f = float(celda.get("f") or 0)
    celda["pu"] = ceil_proy_unidades(u, coef)
    celda["pf"] = round_proy_facturacion(f, coef)


def aplicar_proyeccion_filas(filas: List[Dict[str, Any]], coef: float) -> List[Dict[str, Any]]:
    """Agrega pu/pf en totales_mes, valores_mes y total de cada fila vendedor/cliente."""
    for vend in filas:
        for celda in (vend.get("totales_mes") or {}).values():
            _proyectar_celda(celda, coef)
        if vend.get("total"):
            _proyectar_celda(vend["total"], coef)
        for cli in vend.get("clientes") or []:
            for celda in (cli.get("valores_mes") or {}).values():
                _proyectar_celda(celda, coef)
            if cli.get("total"):
                _proyectar_celda(cli["total"], coef)
    return filas


def _parse_tasa_regalia(filters: Dict[str, Any]) -> float:
    """Acepta tasa_regalia_pct (13 = 13 %) o tasa_regalia (0.13). Default 13 %."""
    raw_frac = filters.get("tasa_regalia")
    if raw_frac is not None and str(raw_frac).strip() != "":
        dec = to_decimal_or_none(raw_frac)
        if dec is not None:
            return float(dec)
    raw_pct = filters.get("tasa_regalia_pct")
    if raw_pct is not None and str(raw_pct).strip() != "":
        dec = to_decimal_or_none(raw_pct)
        if dec is not None:
            return float(dec) / 100.0
    return _TASA_REGALIA_DEFAULT


def _parse_incluir_proyeccion(filters: Dict[str, Any]) -> bool:
    raw = filters.get("incluir_proyeccion")
    if raw is None:
        return False
    s = str(raw).strip().lower()
    return s in ("1", "true", "yes", "si", "sí", "on")


def _parse_coef_proyeccion(filters: Dict[str, Any]) -> float:
    raw = filters.get("coef_proyeccion")
    if raw is None or str(raw).strip() == "":
        return _COEF_PROYECCION_DEFAULT
    dec = to_decimal_or_none(raw)
    return float(dec) if dec is not None else _COEF_PROYECCION_DEFAULT


def _fetch_tc_mysql(cursor) -> Optional[float]:
    try:
        cursor.execute("SELECT ValorPesos FROM cotizacion WHERE id_cotizacion = 1 LIMIT 1")
        row = cursor.fetchone()
        if row and row[0] is not None:
            dec = to_decimal_or_none(row[0])
            if dec is not None and dec > 0:
                return float(dec)
    except Exception:
        pass
    return None


def _resolve_tc(
    cursor,
    filters: Dict[str, Any],
    *,
    base_empresa: Optional[str] = None,
    fecha_corte: Optional[str] = None,
) -> float:
    """TC tipado por el usuario; si vacío, resolver_tc; fallback Excel BEST."""
    raw = filters.get("tc")
    if raw is not None and str(raw).strip() != "":
        dec = to_decimal_or_none(raw)
        if dec is not None and dec > 0:
            return float(dec)
    be = (base_empresa or filters.get("base_empresa") or "").strip()
    if be:
        try:
            from core.services.cotizacion_service import resolver_tc

            corte = fecha_corte or filters.get("fecha_fin") or filters.get("ff_fac")
            resolved = resolver_tc(be, corte, id_cotizacion=1)
            if resolved is not None and resolved > 0:
                return float(resolved)
        except Exception:
            logger.debug("resolver_tc falló; fallback maestro/fijo", exc_info=True)
    from_mysql = _fetch_tc_mysql(cursor) if cursor is not None else None
    if from_mysql is not None:
        return from_mysql
    return float(_TC_FALLBACK)


def _compute_kpis_licencia(kpis_base: Dict[str, float], tasa: float, tc: float) -> Dict[str, float]:
    fact = float(kpis_base.get("facturacion") or 0)
    regalias = fact * tasa
    regalias_tc = regalias / tc if abs(tc) > 1e-9 else 0.0
    return {
        **kpis_base,
        "regalias": regalias,
        "regalias_tc": regalias_tc,
        "tasa_regalia": tasa,
        "tc": tc,
    }


def _celda_vacia() -> Dict[str, float]:
    return {"u": 0.0, "f": 0.0}


def _acumular_celda(dest: Dict[str, Dict[str, float]], mes: str, u: float, f: float) -> None:
    if mes not in dest:
        dest[mes] = _celda_vacia()
    dest[mes]["u"] += u
    dest[mes]["f"] += f


def _total_desde_meses(valores_mes: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    tu = 0.0
    tf = 0.0
    for v in valores_mes.values():
        tu += float(v.get("u") or 0)
        tf += float(v.get("f") or 0)
    return {"u": tu, "f": tf}


def build_filas_matriz(
    rows: List[Dict[str, Any]],
    meses: List[str],
    modo_unidades: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Arma árbol vendedor → clientes desde filas SQL agregadas.
    Retorna (filas, kpis).
    """
    use_docenas = modo_unidades == "docenas"
    meses_set = set(meses)

    por_vendedor: Dict[int, Dict[str, Any]] = {}
    kpis_u = 0.0
    kpis_f = 0.0

    for row in rows:
        ven = to_int_or_none(row.get("ven")) or 0
        mes = str_or_default(row.get("anio_mes"), "")
        if mes not in meses_set:
            continue
        packs = float(row.get("packs") or 0)
        docenas = float(row.get("docenas") or 0)
        fact = float(row.get("facturacion") or 0)
        u = docenas if use_docenas else packs

        kpis_u += u
        kpis_f += fact

        if ven not in por_vendedor:
            por_vendedor[ven] = {
                "tipo": "vendedor",
                "cod": ven,
                "nombre": str_or_default(row.get("vend_nombre"), "").strip() or f"Vendedor {ven}",
                "totales_mes": {},
                "clientes_map": {},
            }
        vend = por_vendedor[ven]
        _acumular_celda(vend["totales_mes"], mes, u, fact)

        cod_cli = str_or_default(row.get("codigo_cliente"), "").strip()
        if cod_cli not in vend["clientes_map"]:
            vend["clientes_map"][cod_cli] = {
                "cod": cod_cli,
                "nombre": str_or_default(row.get("nombre_cliente"), "").strip() or f"Cliente {cod_cli}",
                "valores_mes": {},
            }
        cli = vend["clientes_map"][cod_cli]
        _acumular_celda(cli["valores_mes"], mes, u, fact)

    filas: List[Dict[str, Any]] = []
    for ven in sorted(por_vendedor.keys()):
        vend = por_vendedor[ven]
        clientes = []
        for cod_cli in sorted(vend["clientes_map"].keys(), key=lambda c: vend["clientes_map"][c]["nombre"].lower()):
            cli = vend["clientes_map"][cod_cli]
            clientes.append(
                {
                    "cod": cli["cod"],
                    "nombre": cli["nombre"],
                    "valores_mes": cli["valores_mes"],
                    "total": _total_desde_meses(cli["valores_mes"]),
                }
            )
        filas.append(
            {
                "tipo": "vendedor",
                "cod": vend["cod"],
                "nombre": vend["nombre"],
                "totales_mes": vend["totales_mes"],
                "total": _total_desde_meses(vend["totales_mes"]),
                "clientes": clientes,
            }
        )

    precio_medio = (kpis_f / kpis_u) if abs(kpis_u) > 1e-9 else 0.0
    kpis = {"unidades": kpis_u, "facturacion": kpis_f, "precio_medio": precio_medio}
    return filas, kpis


def sort_filas_vendedores(
    filas: List[Dict[str, Any]],
    *,
    campo: str = "f",
    descendente: bool = True,
) -> List[Dict[str, Any]]:
    """Ordena filas vendedor por total de unidades (u) o facturación (f). Espejo del sort client-side."""
    key = "u" if str(campo).lower() == "u" else "f"
    return sorted(
        filas,
        key=lambda v: float((v.get("total") or {}).get(key) or 0),
        reverse=descendente,
    )


def _sql_rows_ajustes_vmm(cursor, where_cc_parts: List[str], params_cc: List[Any]) -> List[Dict[str, Any]]:
    """Filas de matriz: vendedor sintético × cliente × mes, packs/docenas = 0."""
    out: List[Dict[str, Any]] = []
    for row in consultar_ajustes_sin_mercaderia(
        cursor,
        where_cc_parts,
        params_cc,
        renglon_ok_sql=sql_solo_tipo_art_articulo("art"),
        group_by="cliente_mes",
    ):
        out.append(
            {
                "ven": CODIGO_SINTETICO_AJUSTES,
                "vend_nombre": NOMBRE_AJUSTES,
                "codigo_cliente": str(row.get("codigo_cliente") or ""),
                "nombre_cliente": row.get("nombre_cliente") or "",
                "anio_mes": row.get("anio_mes") or "",
                "packs": 0.0,
                "docenas": 0.0,
                "facturacion": float(row.get("facturacion") or 0),
            }
        )
    return out


def _pin_ajustes_vmm(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return pin_ajustes_al_final(
        filas,
        es_ajuste=lambda v: int(v.get("cod") or 0) == CODIGO_SINTETICO_AJUSTES,
        hijos_key="clientes",
    )


def build_filas_planas_export(
    rows: List[Dict[str, Any]],
    meses: List[str],
    modo_unidades: str,
    coef_proyeccion: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Filas planas Ven × Cliente × AñoMes para export y data[]."""
    use_docenas = modo_unidades == "docenas"
    meses_set = set(meses)
    planas: List[Dict[str, Any]] = []
    for row in rows:
        mes = str_or_default(row.get("anio_mes"), "")
        if mes not in meses_set:
            continue
        packs = float(row.get("packs") or 0)
        docenas = float(row.get("docenas") or 0)
        u = docenas if use_docenas else packs
        fact = float(row.get("facturacion") or 0)
        if abs(u) < 1e-9 and abs(fact) < 0.01:
            continue
        ven = to_int_or_none(row.get("ven")) or 0
        plana: Dict[str, Any] = {
            "cod_viajante": ven,
            "nombre_vendedor": str_or_default(row.get("vend_nombre"), "").strip(),
            "codigo_cliente": str_or_default(row.get("codigo_cliente"), "").strip(),
            "nombre_cliente": str_or_default(row.get("nombre_cliente"), "").strip(),
            "anio_mes": mes,
            "unidades": u,
            "facturacion": fact,
        }
        if coef_proyeccion is not None:
            plana["unidades_proy"] = ceil_proy_unidades(u, coef_proyeccion)
            plana["facturacion_proy"] = round_proy_facturacion(fact, coef_proyeccion)
        planas.append(plana)
    planas.sort(
        key=lambda r: (
            int(r.get("cod_viajante") or 0),
            str(r.get("nombre_vendedor") or "").lower(),
            str(r.get("codigo_cliente") or "").lower(),
            str(r.get("anio_mes") or ""),
        )
    )
    return planas


def aplicar_proyeccion_filas_compare(filas: List[Dict[str, Any]], coef: float) -> List[Dict[str, Any]]:
    """Proyección pu/pf en matriz comparativa (celdas a/b)."""
    for vend in filas:
        for side in ("a", "b"):
            for celda in (vend.get("totales_mes") or {}).values():
                if side in celda:
                    _proyectar_celda(celda[side], coef)
            if vend.get("total") and side in vend["total"]:
                _proyectar_celda(vend["total"][side], coef)
        for cli in vend.get("clientes") or []:
            for celda in (cli.get("valores_mes") or {}).values():
                for side in ("a", "b"):
                    if side in celda:
                        _proyectar_celda(celda[side], coef)
            if cli.get("total"):
                for side in ("a", "b"):
                    if side in cli["total"]:
                        _proyectar_celda(cli["total"][side], coef)
    return filas


def _parse_modo_comparacion(filters: Dict[str, Any]) -> str:
    raw = str_or_default(filters.get("modo_comparacion"), "una").strip().lower()
    return "comparar" if raw == "comparar" else "una"


def _resolve_marca_single(cursor, raw: Any) -> Tuple[Optional[int], str]:
    """Resuelve una marca (CodMarca o NombreMarca) a (cod, nombre)."""
    if raw is None:
        return None, ""
    if isinstance(raw, list):
        if not raw:
            return None, ""
        raw = raw[0]
    s = str_or_default(raw, "").strip()
    if not s:
        return None, ""
    codigos = _resolve_marcas_incluidos(cursor, [raw])
    if not codigos:
        return None, s
    cod = int(codigos[0])
    nombre = s
    try:
        cursor.execute(
            """
            SELECT NombreMarca FROM marca
            WHERE CodMarca = %s AND (anulado IS NULL OR anulado = 'No')
            LIMIT 1
            """,
            [cod],
        )
        row = cursor.fetchone()
        if row and row[0]:
            nombre = str_or_default(row[0], "").strip() or s
    except Exception:
        pass
    return cod, nombre


def _delta_pct_facturacion(fact_a: float, fact_b: float) -> Optional[float]:
    if abs(fact_a) < 1e-9:
        return None if abs(fact_b) < 1e-9 else 100.0
    return round((fact_b - fact_a) / fact_a * 100.0, 2)


def build_filas_matriz_compare(
    rows_a: List[Dict[str, Any]],
    rows_b: List[Dict[str, Any]],
    meses: List[str],
    modo_unidades: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, float], Dict[str, float]]:
    """Matriz comparativa: celdas por mes con claves a/b."""
    filas_a, kpis_a = build_filas_matriz(rows_a, meses, modo_unidades)
    filas_b, kpis_b = build_filas_matriz(rows_b, meses, modo_unidades)
    map_a = {int(v.get("cod") or 0): v for v in filas_a}
    map_b = {int(v.get("cod") or 0): v for v in filas_b}
    all_vends = sorted(set(map_a.keys()) | set(map_b.keys()))

    def _side_cell(vend_map: Dict[int, Dict], vend: int, mes: str, cli_cod: Optional[str] = None) -> Dict[str, float]:
        vend_row = vend_map.get(vend)
        if not vend_row:
            return _celda_vacia()
        if cli_cod is None:
            return dict((vend_row.get("totales_mes") or {}).get(mes) or _celda_vacia())
        for cli in vend_row.get("clientes") or []:
            if str(cli.get("cod")) == str(cli_cod):
                return dict((cli.get("valores_mes") or {}).get(mes) or _celda_vacia())
        return _celda_vacia()

    filas: List[Dict[str, Any]] = []
    for ven in all_vends:
        va = map_a.get(ven)
        vb = map_b.get(ven)
        nombre = (va or vb or {}).get("nombre") or f"Vendedor {ven}"
        clientes_a = {str(c.get("cod")): c for c in (va or {}).get("clientes") or []}
        clientes_b = {str(c.get("cod")): c for c in (vb or {}).get("clientes") or []}
        all_cli = sorted(set(clientes_a.keys()) | set(clientes_b.keys()), key=lambda c: (
            (clientes_a.get(c) or clientes_b.get(c) or {}).get("nombre", c).lower(),
            c,
        ))

        totales_mes: Dict[str, Dict[str, Dict[str, float]]] = {}
        for mes in meses:
            totales_mes[mes] = {
                "a": _side_cell(map_a, ven, mes),
                "b": _side_cell(map_b, ven, mes),
            }
        total_a = (va or {}).get("total") or _celda_vacia()
        total_b = (vb or {}).get("total") or _celda_vacia()

        clientes_out = []
        for cod_cli in all_cli:
            ca = clientes_a.get(cod_cli) or {}
            cb = clientes_b.get(cod_cli) or {}
            valores_mes: Dict[str, Dict[str, Dict[str, float]]] = {}
            for mes in meses:
                valores_mes[mes] = {
                    "a": _side_cell(map_a, ven, mes, cod_cli),
                    "b": _side_cell(map_b, ven, mes, cod_cli),
                }
            clientes_out.append(
                {
                    "cod": cod_cli,
                    "nombre": ca.get("nombre") or cb.get("nombre") or f"Cliente {cod_cli}",
                    "valores_mes": valores_mes,
                    "total": {"a": ca.get("total") or _celda_vacia(), "b": cb.get("total") or _celda_vacia()},
                }
            )

        filas.append(
            {
                "tipo": "vendedor",
                "cod": ven,
                "nombre": nombre,
                "totales_mes": totales_mes,
                "total": {"a": total_a, "b": total_b},
                "clientes": clientes_out,
                "compare": True,
            }
        )

    return filas, kpis_a, kpis_b


def build_filas_planas_compare_export(
    rows_a: List[Dict[str, Any]],
    rows_b: List[Dict[str, Any]],
    meses: List[str],
    modo_unidades: str,
    coef_proyeccion: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Filas planas Ven×Cliente×Mes con columnas u/f por marca A y B."""
    planas_a = build_filas_planas_export(rows_a, meses, modo_unidades, coef_proyeccion)
    planas_b = build_filas_planas_export(rows_b, meses, modo_unidades, coef_proyeccion)
    key_index: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    def _merge_side(planas: List[Dict[str, Any]], side: str) -> None:
        for row in planas:
            key = (
                int(row.get("cod_viajante") or 0),
                str(row.get("codigo_cliente") or ""),
                str(row.get("anio_mes") or ""),
            )
            if key not in key_index:
                key_index[key] = {
                    "cod_viajante": key[0],
                    "nombre_vendedor": row.get("nombre_vendedor") or "",
                    "codigo_cliente": key[1],
                    "nombre_cliente": row.get("nombre_cliente") or "",
                    "anio_mes": key[2],
                    "unidades_a": 0.0,
                    "facturacion_a": 0.0,
                    "unidades_b": 0.0,
                    "facturacion_b": 0.0,
                }
            dest = key_index[key]
            if side == "a":
                dest["unidades_a"] = float(row.get("unidades") or 0)
                dest["facturacion_a"] = float(row.get("facturacion") or 0)
                if "unidades_proy" in row:
                    dest["unidades_proy_a"] = row.get("unidades_proy")
                    dest["facturacion_proy_a"] = row.get("facturacion_proy")
            else:
                dest["unidades_b"] = float(row.get("unidades") or 0)
                dest["facturacion_b"] = float(row.get("facturacion") or 0)
                if "unidades_proy" in row:
                    dest["unidades_proy_b"] = row.get("unidades_proy")
                    dest["facturacion_proy_b"] = row.get("facturacion_proy")

    _merge_side(planas_a, "a")
    _merge_side(planas_b, "b")
    out = list(key_index.values())
    out.sort(
        key=lambda r: (
            int(r.get("cod_viajante") or 0),
            str(r.get("nombre_vendedor") or "").lower(),
            str(r.get("codigo_cliente") or "").lower(),
            str(r.get("anio_mes") or ""),
        )
    )
    return out


def _resolve_marcas_incluidos(cursor, raw: Any) -> List[int]:
    """Acepta CodMarca (int) o NombreMarca (str) en la lista."""
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    elif not isinstance(raw, list):
        raw = []
    codigos: List[int] = []
    nombres: List[str] = []
    for item in raw:
        cod = to_int_or_none(item)
        if cod is not None:
            codigos.append(int(cod))
        else:
            n = str_or_default(item, "").strip()
            if n:
                nombres.append(n)
    if nombres:
        ph = ",".join(["%s"] * len(nombres))
        cursor.execute(
            f"""
            SELECT CodMarca FROM marca
            WHERE (anulado IS NULL OR anulado = 'No')
              AND NombreMarca IN ({ph})
            """,
            nombres,
        )
        for r in cursor.fetchall():
            c = to_int_or_none(r[0])
            if c is not None:
                codigos.append(int(c))
    return sorted(set(codigos))


def run_ventas_marcas_mensual(report: ReportDefinition, payload: Dict, user) -> QueryResult:
    svc = QueryRunnerService(user)
    filters = payload.get("filters", {}) or {}

    fecha_inicio, fecha_fin = svc._resolve_period_dates(filters)
    fi_fac_raw = filters.get("fecha_inicio_facturacion")
    ff_fac_raw = filters.get("fecha_fin_facturacion")
    fi_fac = str_or_default(fi_fac_raw, "").strip() or fecha_inicio
    ff_fac = str_or_default(ff_fac_raw, "").strip() or fecha_fin

    if not fi_fac or not ff_fac:
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
        )

    base_empresa = filters.get("base_empresa")
    if not base_empresa and hasattr(user, "base_empresa"):
        base_empresa = getattr(user, "base_empresa", None)
    if not base_empresa:
        base_empresa = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    if not base_empresa:
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=["No se pudo determinar la base de datos de la empresa."],
        )

    modo_unidades = str_or_default(filters.get("modo_unidades"), "packs").strip().lower()
    if modo_unidades not in ("packs", "docenas"):
        modo_unidades = "packs"

    sucursales_ints, puntos_venta_ints = svc._parse_sucursales_pv(filters)
    clientes_excluidos = svc._parse_clientes_excluidos(filters)
    vendedores_excluidos = svc._parse_vendedores_excluidos(filters)
    clientes_incluir = _parse_int_list(filters.get("clientes_incluir", []))
    vendedores_incluir = _parse_int_list(filters.get("vendedores_incluir", []))

    raw_marcas = filters.get("marcas_incluidos")
    if raw_marcas is None:
        raw_marcas = filters.get("marcas_incluidas")
    superarts = _parse_str_list(filters.get("superarts_incluidos"))
    if not superarts:
        superarts = _parse_str_list(filters.get("id_manuales"))

    modo_comparacion = _parse_modo_comparacion(filters)
    marca_a_raw = filters.get("marca_a")
    marca_b_raw = filters.get("marca_b")

    alcance_ctx = ctx_desde_runner(user, str(base_empresa), filters)
    try:
        alcance_cv = alcance_objetivos_cod_viajante(str(base_empresa), alcance_ctx)
    except Exception:
        # No continuar sin alcance: una caída de la configuración comercial no
        # debe convertir el endpoint en 500 ni exponer ventas sin restricción.
        logger.exception("ventas_marcas_mensual: no se pudo validar el alcance comercial")
        return QueryResult(
            meta={
                "slug": report.slug,
                "name": report.name,
                "category": report.category,
                "version": report.version,
                "extra": {
                    "modo_unidades": modo_unidades,
                    "meses": [],
                    "kpis": {
                        "unidades": 0,
                        "facturacion": 0,
                        "precio_medio": 0,
                        "regalias": 0,
                        "regalias_tc": 0,
                    },
                    "filas": [],
                },
            },
            data=[],
            totals={},
            notes=["Error al validar el alcance comercial; no se mostrarán datos."],
        )

    clientes_excluidos = [c for c in clientes_excluidos if to_int_or_none(c) not in set(clientes_incluir)]
    vendedores_excluidos = [v for v in vendedores_excluidos if int(v) not in set(vendedores_incluir)]

    alcance_viaj_filtro: List[int] = []
    if alcance_cv is not None:
        if not alcance_cv:
            return QueryResult(
                meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                data=[],
                totals={},
                notes=["Sin vendedores en el alcance comercial del usuario."],
            )
        alcance_set = set(int(x) for x in alcance_cv)
        if vendedores_incluir:
            alcance_viaj_filtro = [v for v in vendedores_incluir if v in alcance_set]
            if not alcance_viaj_filtro:
                return QueryResult(
                    meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                    data=[],
                    totals={},
                    notes=["Los vendedores solicitados no están en su alcance comercial."],
                )
        else:
            alcance_viaj_filtro = sorted(alcance_set)
        vendedores_excluidos = [v for v in vendedores_excluidos if int(v) not in set(alcance_viaj_filtro)]

    fi_sql = _norm_yyyy_mm_dd(fi_fac)
    ff_sql = _norm_yyyy_mm_dd(ff_fac)

    signo_qty = sql_signo_qty_expr()
    signo_imp = sql_signo_imp_post_pie_expr()
    factor_sql = _sql_factor_docenas_expr()

    where_parts = sql_base_where_clauses()
    params: List[Any] = [fi_sql, ff_sql]
    where_cc_parts = [
        "cc.Fecha >= %s",
        "cc.Fecha <= %s",
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
        f"cc.TipoComprobante IN ({sql_comprobantes_in_clause()})",
    ]
    params_cc: List[Any] = [fi_sql, ff_sql]

    def _append_cc_filter(clause: str, values: List[Any]) -> None:
        where_parts.append(clause)
        params.extend(values)
        where_cc_parts.append(clause)
        params_cc.extend(values)

    if sucursales_ints:
        phs = ",".join(["%s"] * len(sucursales_ints))
        _append_cc_filter(f"cc.CodSucursal IN ({phs})", sucursales_ints)
    if puntos_venta_ints:
        phpv = ",".join(["%s"] * len(puntos_venta_ints))
        _append_cc_filter(f"cc.id_pv IN ({phpv})", puntos_venta_ints)
    if clientes_excluidos:
        ph = ",".join(["%s"] * len(clientes_excluidos))
        _append_cc_filter(f"cc.Codigo NOT IN ({ph})", clientes_excluidos)
    if clientes_incluir:
        ph = ",".join(["%s"] * len(clientes_incluir))
        _append_cc_filter(f"cc.Codigo IN ({ph})", clientes_incluir)
    if vendedores_excluidos:
        phv = ",".join(["%s"] * len(vendedores_excluidos))
        _append_cc_filter(f"cc.CodViajante NOT IN ({phv})", vendedores_excluidos)
    if vendedores_incluir:
        phvi = ",".join(["%s"] * len(vendedores_incluir))
        _append_cc_filter(f"cc.CodViajante IN ({phvi})", vendedores_incluir)
    if alcance_viaj_filtro:
        alcance_sql, alcance_params = _sql_in_viajantes("cc", alcance_viaj_filtro)
        _append_cc_filter(alcance_sql.lstrip(" AND "), alcance_params)

    where_parts_base = list(where_parts)
    params_base = list(params)

    sql_rows: List[Dict[str, Any]] = []
    marcas_incluidos: List[int] = []
    aviso_meses: Optional[str] = None
    um_desconocidas: Set[str] = set()
    tc_efectivo = float(_TC_FALLBACK)
    tasa_regalia = _parse_tasa_regalia(filters)
    incluir_proyeccion = _parse_incluir_proyeccion(filters)
    coef_proyeccion = _parse_coef_proyeccion(filters)
    compare_meta: Optional[Dict[str, Any]] = None
    export_detalle = bool(payload.get("_export_detalle"))
    detalle_rows: Optional[List[Dict[str, Any]]] = None

    try:
        pool = get_mysql_pool()
        with pool.get_connection(str(base_empresa).strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SET SESSION max_execution_time = 90000")
            except Exception:
                pass

            tc_efectivo = _resolve_tc(cursor, filters, base_empresa=str(base_empresa).strip(), fecha_corte=ff_sql)

            if modo_comparacion == "comparar":
                cod_a, nom_a = _resolve_marca_single(cursor, marca_a_raw)
                cod_b, nom_b = _resolve_marca_single(cursor, marca_b_raw)
                if cod_a is None or cod_b is None:
                    return QueryResult(
                        meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                        data=[],
                        totals={},
                        notes=["En modo comparar debe seleccionar marca A y marca B."],
                    )
                if cod_a == cod_b:
                    return QueryResult(
                        meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                        data=[],
                        totals={},
                        notes=["Las marcas A y B deben ser distintas."],
                    )
                marcas_incluidos = [cod_a, cod_b]

                def _run_for_marca(cod_marca: int) -> List[Dict[str, Any]]:
                    cat_sql, cat_params = _vo_sql_filtros_articulo("art", marcas_incluidos=[cod_marca])
                    if superarts:
                        ph_sa = ",".join(["%s"] * len(superarts))
                        cat_sql += f" AND art.id_manual IN ({ph_sa})"
                        cat_params = list(cat_params) + superarts
                    where_s = " AND ".join(where_parts) + cat_sql
                    sql = f"""
                        SELECT
                            cc.CodViajante AS ven,
                            COALESCE(v.Nombre, '') AS vend_nombre,
                            cc.Codigo AS codigo_cliente,
                            COALESCE(cl.nombre_cliente, '') AS nombre_cliente,
                            DATE_FORMAT(cc.Fecha, '%%Y%%m') AS anio_mes,
                            SUM({signo_qty}) AS packs,
                            SUM({signo_qty} / {factor_sql}) AS docenas,
                            SUM({signo_imp}) AS facturacion,
                            GROUP_CONCAT(DISTINCT COALESCE(st.nombre_unimed_vta, um.nombre_unimed, '') SEPARATOR ',') AS ums_raw
                        FROM stock st
                        INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
                        INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
                        LEFT JOIN articulo art ON art.IDArt = st.IDArt
                        LEFT JOIN unidmed um ON um.id_unimed = art.id_unimed
                        LEFT JOIN viajantes v ON v.CodViajante = cc.CodViajante
                        WHERE {where_s}
                        GROUP BY cc.CodViajante, v.Nombre, cc.Codigo, cl.nombre_cliente, DATE_FORMAT(cc.Fecha, '%%Y%%m')
                        HAVING ABS(packs) > 0.00001 OR ABS(facturacion) > 0.01
                    """
                    cursor.execute(sql, params + cat_params)
                    cols = [d[0] for d in cursor.description]
                    rows_m: List[Dict[str, Any]] = []
                    for r in cursor.fetchall():
                        row = dict(zip(cols, r))
                        ums_raw = str_or_default(row.pop("ums_raw", ""), "")
                        for um_token in ums_raw.split(","):
                            um_t = um_token.strip().upper()
                            if um_t and um_t not in _FACTOR_DOCENAS_MAP:
                                um_desconocidas.add(um_t)
                        rows_m.append(row)
                    return rows_m

                sql_rows_a = _run_for_marca(cod_a)
                sql_rows_b = _run_for_marca(cod_b)
                sql_rows = sql_rows_a + sql_rows_b
                compare_meta = {
                    "cod_a": cod_a,
                    "nom_a": nom_a,
                    "cod_b": cod_b,
                    "nom_b": nom_b,
                    "rows_a": sql_rows_a,
                    "rows_b": sql_rows_b,
                }
            else:
                compare_meta = None
                marcas_incluidos = _resolve_marcas_incluidos(cursor, raw_marcas)
                cat_sql, cat_params = _vo_sql_filtros_articulo(
                    "art",
                    marcas_incluidos=marcas_incluidos,
                )
                if superarts:
                    ph_sa = ",".join(["%s"] * len(superarts))
                    cat_sql += f" AND art.id_manual IN ({ph_sa})"
                    cat_params = list(cat_params) + superarts

                where_s = " AND ".join(where_parts) + cat_sql

                sql = f"""
                    SELECT
                        cc.CodViajante AS ven,
                        COALESCE(v.Nombre, '') AS vend_nombre,
                        cc.Codigo AS codigo_cliente,
                        COALESCE(cl.nombre_cliente, '') AS nombre_cliente,
                        DATE_FORMAT(cc.Fecha, '%%Y%%m') AS anio_mes,
                        SUM({signo_qty}) AS packs,
                        SUM({signo_qty} / {factor_sql}) AS docenas,
                        SUM({signo_imp}) AS facturacion,
                        GROUP_CONCAT(DISTINCT COALESCE(st.nombre_unimed_vta, um.nombre_unimed, '') SEPARATOR ',') AS ums_raw
                    FROM stock st
                    INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
                    INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
                    LEFT JOIN articulo art ON art.IDArt = st.IDArt
                    LEFT JOIN unidmed um ON um.id_unimed = art.id_unimed
                    LEFT JOIN viajantes v ON v.CodViajante = cc.CodViajante
                    WHERE {where_s}
                    GROUP BY cc.CodViajante, v.Nombre, cc.Codigo, cl.nombre_cliente, DATE_FORMAT(cc.Fecha, '%%Y%%m')
                    HAVING ABS(packs) > 0.00001 OR ABS(facturacion) > 0.01
                """
                cursor.execute(sql, params + cat_params)
                cols = [d[0] for d in cursor.description]
                for r in cursor.fetchall():
                    row = dict(zip(cols, r))
                    ums_raw = str_or_default(row.pop("ums_raw", ""), "")
                    for um_token in ums_raw.split(","):
                        um_t = um_token.strip().upper()
                        if um_t and um_t not in _FACTOR_DOCENAS_MAP:
                            um_desconocidas.add(um_t)
                    sql_rows.append(row)

                if not filtros_catalogo_restringen(
                    marcas_incluidos=marcas_incluidos,
                    superarts=superarts,
                ):
                    sql_rows.extend(_sql_rows_ajustes_vmm(cursor, where_cc_parts, params_cc))

            if export_detalle:
                from reports.services.ventas_marcas_mensual_export import fetch_detalle_for_filters

                where_s_det = " AND ".join(where_parts_base)
                try:
                    detalle_rows = fetch_detalle_for_filters(
                        cursor,
                        filters,
                        where_s=where_s_det,
                        params=list(params_base),
                        raw_marcas=raw_marcas,
                        superarts=superarts,
                    )
                except Exception as ex_det:
                    logger.exception("ventas_marcas_mensual: error SQL en hoja Detalle")
                    detalle_rows = []
                    aviso_detalle = (
                        f"Error al armar la hoja Detalle: {ex_det}. "
                        "La matriz se exportó con los datos disponibles."
                    )
                    if aviso_meses:
                        aviso_meses = f"{aviso_meses} {aviso_detalle}"
                    else:
                        aviso_meses = aviso_detalle

    except Exception as ex:
        logger.exception("ventas_marcas_mensual: error SQL")
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=[f"Error al ejecutar la consulta: {ex}"],
        )

    meses_all = sorted({str_or_default(r.get("anio_mes"), "") for r in sql_rows if r.get("anio_mes")})
    meses = meses_all
    if len(meses_all) > _MAX_MESES:
        meses = meses_all[-_MAX_MESES:]
        aviso_meses = (
            f"El período incluye {len(meses_all)} meses; se muestran los {_MAX_MESES} más recientes."
        )

    filas: List[Dict[str, Any]]
    kpis: Dict[str, float]
    planas: List[Dict[str, Any]]

    if compare_meta:
        filas, kpis_a, kpis_b = build_filas_matriz_compare(
            compare_meta["rows_a"],
            compare_meta["rows_b"],
            meses,
            modo_unidades,
        )
        kpis_a_full = _compute_kpis_licencia(kpis_a, tasa_regalia, tc_efectivo)
        kpis_b_full = _compute_kpis_licencia(kpis_b, tasa_regalia, tc_efectivo)
        delta_pct = _delta_pct_facturacion(
            float(kpis_a_full.get("facturacion") or 0),
            float(kpis_b_full.get("facturacion") or 0),
        )
        kpis = {
            "unidades": float(kpis_a_full.get("unidades") or 0) + float(kpis_b_full.get("unidades") or 0),
            "facturacion": float(kpis_a_full.get("facturacion") or 0) + float(kpis_b_full.get("facturacion") or 0),
            "precio_medio": 0.0,
            "regalias": float(kpis_a_full.get("regalias") or 0) + float(kpis_b_full.get("regalias") or 0),
            "regalias_tc": float(kpis_a_full.get("regalias_tc") or 0) + float(kpis_b_full.get("regalias_tc") or 0),
            "tasa_regalia": tasa_regalia,
            "tc": tc_efectivo,
        }
        u_tot = float(kpis.get("unidades") or 0)
        if abs(u_tot) > 1e-9:
            kpis["precio_medio"] = float(kpis.get("facturacion") or 0) / u_tot
        coef_proy_activo = coef_proyeccion if incluir_proyeccion else None
        if incluir_proyeccion:
            aplicar_proyeccion_filas_compare(filas, coef_proyeccion)
        planas = build_filas_planas_compare_export(
            compare_meta["rows_a"],
            compare_meta["rows_b"],
            meses,
            modo_unidades,
            coef_proy_activo,
        )
    else:
        filas, kpis_base = build_filas_matriz(sql_rows, meses, modo_unidades)
        filas = _pin_ajustes_vmm(filas)
        kpis = _compute_kpis_licencia(kpis_base, tasa_regalia, tc_efectivo)
        coef_proy_activo = coef_proyeccion if incluir_proyeccion else None
        if incluir_proyeccion:
            aplicar_proyeccion_filas(filas, coef_proyeccion)
        planas = build_filas_planas_export(sql_rows, meses, modo_unidades, coef_proy_activo)

    extra: Dict[str, Any] = {
        "modo_unidades": modo_unidades,
        "meses": meses,
        "kpis": kpis,
        "filas": filas,
    }
    if incluir_proyeccion:
        extra["proyeccion"] = {"activa": True, "coef": coef_proyeccion}
    if aviso_meses:
        extra["aviso_meses"] = aviso_meses
    if um_desconocidas:
        extra["um_desconocidas"] = sorted(um_desconocidas)
    if compare_meta:
        extra["compare"] = {
            "activo": True,
            "marca_a": {
                "cod": compare_meta["cod_a"],
                "nombre": compare_meta["nom_a"],
                "kpis": kpis_a_full,
            },
            "marca_b": {
                "cod": compare_meta["cod_b"],
                "nombre": compare_meta["nom_b"],
                "kpis": kpis_b_full,
            },
            "delta_pct_facturacion": delta_pct,
        }
        extra["modo_comparacion"] = "comparar"
    else:
        extra["modo_comparacion"] = "una"
    if detalle_rows is not None:
        extra["detalle_rows"] = detalle_rows

    filters_applied = {
        "fecha_inicio_facturacion": fi_sql,
        "fecha_fin_facturacion": ff_sql,
        "modo_unidades": modo_unidades,
        "marcas_incluidos": marcas_incluidos,
        "superarts_incluidos": superarts,
        "sucursales": sucursales_ints,
        "punto_venta": puntos_venta_ints,
        "clientes_excluidos": clientes_excluidos,
        "clientes_incluir": clientes_incluir,
        "vendedores_excluidos": vendedores_excluidos,
        "vendedores_incluir": vendedores_incluir,
        "base_empresa_used": str(base_empresa),
        "tasa_regalia_pct": tasa_regalia * 100.0,
        "tasa_regalia": tasa_regalia,
        "tc": tc_efectivo,
        "incluir_proyeccion": incluir_proyeccion,
        "coef_proyeccion": coef_proyeccion if incluir_proyeccion else None,
        "modo_comparacion": modo_comparacion,
        "marca_a": compare_meta["cod_a"] if compare_meta else None,
        "marca_b": compare_meta["cod_b"] if compare_meta else None,
    }

    notes: List[str] = []
    if aviso_meses:
        notes.append(aviso_meses)
    if any(int(v.get("cod") or 0) == CODIGO_SINTETICO_AJUSTES for v in filas):
        notes.append(NOTA_AJUSTES_INCLUIDOS)
    elif not compare_meta and filtros_catalogo_restringen(
        marcas_incluidos=marcas_incluidos,
        superarts=superarts,
    ):
        notes.append(NOTA_AJUSTES_OMITIDOS_CATALOGO)

    return QueryResult(
        meta={
            "slug": report.slug,
            "name": report.name,
            "category": report.category,
            "version": report.version,
            "filters_applied": filters_applied,
            "extra": extra,
        },
        data=planas,
        totals={
            "unidades": kpis["unidades"],
            "facturacion": kpis["facturacion"],
            "precio_medio": kpis["precio_medio"],
            "regalias": kpis["regalias"],
            "regalias_tc": kpis["regalias_tc"],
        },
        notes=notes,
    )
