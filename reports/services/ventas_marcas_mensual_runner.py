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

_TIPOS_FAC = ("FA", "FB", "FC", "FE", "FM")
_TIPOS_NC = ("NCA", "NCB", "NCC", "NCE", "NCM")
_STOCK_TIPO_COMP = ("Venta", "Venta TPV", "Devol - Cliente", "ND Anul NC")

_FACTOR_DOCENAS_MAP = {
    "P1": 12.0,
    "P2": 6.0,
    "P3": 4.0,
    "P6": 2.0,
    "CU": 1.0,
}


def factor_docenas_unimed(nombre_unimed: Optional[str]) -> float:
    """Factor tipo Excel Canti_2: divisor para obtener docenas desde packs."""
    um = str_or_default(nombre_unimed, "").strip().upper()
    return _FACTOR_DOCENAS_MAP.get(um, 1.0)


def _sql_factor_docenas_expr() -> str:
    return """
        CASE COALESCE(st.nombre_unimed_vta, um.nombre_unimed, '')
            WHEN 'P1' THEN 12
            WHEN 'P2' THEN 6
            WHEN 'P3' THEN 4
            WHEN 'P6' THEN 2
            WHEN 'CU' THEN 1
            ELSE 1
        END
    """


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
    d = to_date_or_none(raw)
    if d is None:
        return str_or_default(raw, "").strip()[:10]
    return d.isoformat()


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


def _resolve_tc(cursor, filters: Dict[str, Any]) -> float:
    """TC tipado por el usuario; si vacío, cotización MySQL id=1; fallback Excel BEST."""
    raw = filters.get("tc")
    if raw is not None and str(raw).strip() != "":
        dec = to_decimal_or_none(raw)
        if dec is not None and dec > 0:
            return float(dec)
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

    alcance_ctx = ctx_desde_runner(user, str(base_empresa), filters)
    alcance_cv = alcance_objetivos_cod_viajante(str(base_empresa), alcance_ctx)

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

    signo_qty = """
        CASE
            WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(st.Cantidad, 0)
            WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(st.Cantidad, 0)
            ELSE 0
        END
    """
    signo_imp = """
        CASE
            WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(st.PrecioNetoxR, 0)
            WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(st.PrecioNetoxR, 0)
            ELSE 0
        END
    """
    factor_sql = _sql_factor_docenas_expr()

    where_parts = [
        "cc.Fecha >= %s",
        "cc.Fecha <= %s",
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
        "cc.TipoComprobante IN ('FA','FB','FC','FE','FM','NCA','NCB','NCC','NCE','NCM')",
        "st.Anulado = 'No'",
        "st.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')",
    ]
    params: List[Any] = [fi_sql, ff_sql]

    if sucursales_ints:
        phs = ",".join(["%s"] * len(sucursales_ints))
        where_parts.append(f"cc.CodSucursal IN ({phs})")
        params.extend(sucursales_ints)
    if puntos_venta_ints:
        phpv = ",".join(["%s"] * len(puntos_venta_ints))
        where_parts.append(f"cc.id_pv IN ({phpv})")
        params.extend(puntos_venta_ints)
    if clientes_excluidos:
        ph = ",".join(["%s"] * len(clientes_excluidos))
        where_parts.append(f"cc.Codigo NOT IN ({ph})")
        params.extend(clientes_excluidos)
    if clientes_incluir:
        ph = ",".join(["%s"] * len(clientes_incluir))
        where_parts.append(f"cc.Codigo IN ({ph})")
        params.extend(clientes_incluir)
    if vendedores_excluidos:
        phv = ",".join(["%s"] * len(vendedores_excluidos))
        where_parts.append(f"cc.CodViajante NOT IN ({phv})")
        params.extend(vendedores_excluidos)
    if vendedores_incluir:
        phvi = ",".join(["%s"] * len(vendedores_incluir))
        where_parts.append(f"cc.CodViajante IN ({phvi})")
        params.extend(vendedores_incluir)
    if alcance_viaj_filtro:
        alcance_sql, alcance_params = _sql_in_viajantes("cc", alcance_viaj_filtro)
        where_parts.append(alcance_sql.lstrip(" AND "))
        params.extend(alcance_params)

    sql_rows: List[Dict[str, Any]] = []
    marcas_incluidos: List[int] = []
    aviso_meses: Optional[str] = None
    um_desconocidas: Set[str] = set()
    tc_efectivo = float(_TC_FALLBACK)
    tasa_regalia = _parse_tasa_regalia(filters)
    incluir_proyeccion = _parse_incluir_proyeccion(filters)
    coef_proyeccion = _parse_coef_proyeccion(filters)

    try:
        pool = get_mysql_pool()
        with pool.get_connection(str(base_empresa).strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SET SESSION max_execution_time = 90000")
            except Exception:
                pass

            tc_efectivo = _resolve_tc(cursor, filters)

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
                    DATE_FORMAT(cc.Fecha, '%Y%m') AS anio_mes,
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
                GROUP BY cc.CodViajante, v.Nombre, cc.Codigo, cl.nombre_cliente, DATE_FORMAT(cc.Fecha, '%Y%m')
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

    filas, kpis_base = build_filas_matriz(sql_rows, meses, modo_unidades)
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
    }

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
        notes=[aviso_meses] if aviso_meses else [],
    )
