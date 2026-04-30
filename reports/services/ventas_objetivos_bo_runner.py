# -*- coding: utf-8 -*-
"""
Informe Objetivos de ventas por vendedor (jerárquico vendedor → cliente).

Misma temporalidad dual que bo-stock-facturacion. Ver SPEC_INFORME_OBJETIVOS_VENTAS_BO.md.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Set, Tuple

from django.conf import settings
from django.utils import timezone

from core.models import UsuarioExtendido
from reports.models import ReportDefinition, ReportExecutionLog
from reports.services.connection_pool import get_mysql_pool
from reports.services.objetivos_ventas_contract import (
    calcular_falta,
    calcular_total_consolidado_objetivos,
)
from reports.services.query_runner import QueryResult, QueryRunnerService, parse_fecha_bo_yyyymmdd

logger = logging.getLogger(__name__)


def _usuario_es_supervisor_cod(user) -> bool:
    """
    Solo el usuario administraNET con cod_usuario 'supervisor' (minúsculas).
    No equivale al puesto/rol «Supervisor» ni a superuser Django sin ese cod_usuario.
    """
    if not user:
        return False
    cod = getattr(user, "cod_usuario", None) or ""
    return str(cod).strip().lower() == "supervisor"


def _filters_applied_para_respuesta(filters_applied: Dict[str, Any], user) -> Dict[str, Any]:
    """Quita métricas de performance del payload hacia el cliente si no es usuario supervisor."""
    out = dict(filters_applied or {})
    if not _usuario_es_supervisor_cod(user):
        out.pop("performance_phase_ms", None)
        out.pop("performance_total_ms", None)
    return out

_TIPOS_FAC_NC = (
    "FA",
    "FB",
    "FC",
    "FE",
    "FM",
    "NCA",
    "NCB",
    "NCC",
    "NCE",
    "NCM",
)
_STOCK_TIPO_COMP_VENTAS = (
    "Venta",
    "Venta TPV",
    "Devol - Cliente",
    "ND Anul NC",
)

# Misma convención que `bo-stock-facturacion` / VB6 Info_Stock (0–6).
_LISTA_PRECIO_LABELS = (
    "Costo",
    "Lista Oficial",
    "Lista 1",
    "Lista 2",
    "Lista 3",
    "Lista 4",
    "Lista 5",
)


def _label_lista_precio(cod: int) -> str:
    if 0 <= cod < len(_LISTA_PRECIO_LABELS):
        return _LISTA_PRECIO_LABELS[cod]
    return f"Lista ({cod})"


_METRIC_ORDER_MAP = {
    "objetivo_meta": "objetivo",
    "objetivo_falta": "falta",
    "total_ventas_periodo": "total",
}

_ORDER_DIRECTION_MAP = {
    "asc": 1,
    "desc": -1,
}


def _parse_int_list(raw: Any) -> List[int]:
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    elif not isinstance(raw, list):
        raw = []
    out: List[int] = []
    for item in raw:
        try:
            out.append(int(str(item).strip()))
        except (TypeError, ValueError):
            continue
    return out


def _parse_sorting(filters: Dict[str, Any]) -> Tuple[str, str]:
    raw_field = str(filters.get("ordenar_por") or "objetivo_meta").strip().lower()
    raw_dir = str(filters.get("orden_forma") or "desc").strip().lower()
    field = raw_field if raw_field in _METRIC_ORDER_MAP else "objetivo_meta"
    direction = raw_dir if raw_dir in _ORDER_DIRECTION_MAP else "desc"
    return field, direction


def _sort_scalar(value: Any, direction: str) -> float:
    n = float(value or 0)
    return n if direction == "asc" else -n


def _alpha_id_key(item: Dict[str, Any], name_key: str, id_key: str) -> Tuple[str, int]:
    return ((item.get(name_key) or "").strip().upper(), int(item.get(id_key) or 0))


def _group_metric(node: Dict[str, Any], metric_key: str) -> float:
    if metric_key == "falta":
        return float(node.get("falta") or 0)
    if metric_key == "total":
        raw = node.get("total")
        if raw is not None:
            return float(raw or 0)
        return float(node.get("facturacion") or 0)
    if metric_key == "objetivo":
        return float(node.get("objetivo") or 0)
    return float(node.get(metric_key) or 0)


def _sort_nested_detalle(detalle: List[Dict[str, Any]], metric_key: str, direction: str) -> List[Dict[str, Any]]:
    def _sort_art(arts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            arts,
            key=lambda a: (
                _sort_scalar(_group_metric(a, metric_key), direction),
                (a.get("nombre_articulo") or "").strip().upper(),
                int(a.get("id_art") or 0),
            ),
        )

    out: List[Dict[str, Any]] = []
    for rub in detalle or []:
        rub_copy = dict(rub)
        subrows = []
        for sub in rub_copy.get("children") or []:
            sub_copy = dict(sub)
            sub_copy["children"] = _sort_art(sub_copy.get("children") or [])
            subrows.append(sub_copy)
        rub_copy["children"] = sorted(
            subrows,
            key=lambda s: (
                _sort_scalar(_group_metric(s, metric_key), direction),
                (s.get("nombre_subrubro") or "").strip().upper(),
                int(s.get("id_subrubro") or 0),
            ),
        )
        out.append(rub_copy)
    return sorted(
        out,
        key=lambda r: (
            _sort_scalar(_group_metric(r, metric_key), direction),
            (r.get("nombre_rubro") or "").strip().upper(),
            int(r.get("codigo_rubro") or 0),
        ),
    )


def _persist_perf_log(
    report: ReportDefinition,
    user,
    filters_snapshot: Dict[str, Any],
    phase_ms: Dict[str, int],
    total_ms: int,
    status: str,
    note: str = "",
) -> None:
    executed_by_user = None
    if isinstance(user, UsuarioExtendido) and getattr(user, "is_authenticated", False):
        executed_by_user = user

    payload = dict(filters_snapshot or {})
    payload["performance"] = {
        "phase_ms": phase_ms,
        "duration_total_ms": total_ms,
        "status": status,
    }
    payload["request_context"] = {
        "timestamp": timezone.now().isoformat(),
        "report_slug": report.slug,
        "username": getattr(executed_by_user, "username", None),
    }

    log = ReportExecutionLog.objects.create(
        report=report,
        executed_by=executed_by_user,
        status=status,
        filters_snapshot=payload,
        duration_ms=max(int(total_ms), 0),
        notes=note or "",
    )
    old_logs = (
        ReportExecutionLog.objects.filter(report=report, executed_by=executed_by_user)
        .order_by("-executed_at", "-id")
        .values_list("id", flat=True)[10:]
    )
    if old_logs:
        ReportExecutionLog.objects.filter(id__in=list(old_logs)).delete()


def _norm_yyyy_mm_dd(s: str) -> str:
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s[:10] if len(s) >= 10 else s


def _parse_date_for_overlap(s: str):
    s2 = _norm_yyyy_mm_dd(s)
    return datetime.strptime(s2, "%Y-%m-%d").date()


def _nest_venta_detalle_rubro_subrubro_articulo(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Construye rubro → subrubro → artículo con facturación y unidades por línea (ventas netas del período).
    Los **remitos** del cliente solo existen a nivel cabecera (`comp_ped` REM); no se reparten en el árbol.
    El BO se fusiona después con `_merge_bo_en_detalle_arbol`; las agregaciones de venta se recalculan con
    `_rollup_facturacion_unidades_detalle` tras incorporar artículos solo-BO.
    """
    rubros: Dict[Tuple[int, str], Dict[str, Any]] = {}
    sub_idx: Dict[Tuple[Tuple[int, str], Tuple[int, str]], Dict[str, Any]] = {}

    for rw in filas:
        cr = int(rw.get("codigo_rubro") or 0)
        nr = (rw.get("nombre_rubro") or "").strip() or "Sin rubro"
        isr = int(rw.get("id_subrubro") or 0)
        nsr = (rw.get("nombre_subrubro") or "").strip() or "Sin subrubro"
        iar = int(rw.get("id_art") or 0)
        nar = (rw.get("nombre_articulo") or "").strip() or "Sin artículo"
        fac = float(rw.get("facturacion") or 0)
        uni = float(rw.get("cantidades_vendidas") or 0)

        rk = (cr, nr)
        if rk not in rubros:
            rubros[rk] = {
                "tipo": "rubro",
                "codigo_rubro": cr,
                "nombre_rubro": nr,
                "facturacion": 0.0,
                "cantidades_vendidas": 0.0,
                "children": [],
            }
        rubros[rk]["facturacion"] += fac
        rubros[rk]["cantidades_vendidas"] += uni

        sk = (rk, (isr, nsr))
        if sk not in sub_idx:
            node = {
                "tipo": "subrubro",
                "id_subrubro": isr,
                "nombre_subrubro": nsr,
                "facturacion": 0.0,
                "cantidades_vendidas": 0.0,
                "children": [],
            }
            sub_idx[sk] = node
            rubros[rk]["children"].append(node)
        sub_idx[sk]["facturacion"] += fac
        sub_idx[sk]["cantidades_vendidas"] += uni

        sub_idx[sk]["children"].append(
            {
                "tipo": "articulo",
                "id_art": iar,
                "nombre_articulo": nar,
                "facturacion": fac,
                "cantidades_vendidas": uni,
            }
        )

    def sort_key_rub(x: Dict[str, Any]) -> Tuple[str, int]:
        return ((x.get("nombre_rubro") or "").upper(), int(x.get("codigo_rubro") or 0))

    out = list(rubros.values())
    out.sort(key=sort_key_rub)
    for rb in out:
        ch = rb.get("children") or []
        ch.sort(key=lambda s: ((s.get("nombre_subrubro") or "").upper(), int(s.get("id_subrubro") or 0)))
        for su in ch:
            arts = su.get("children") or []
            arts.sort(key=lambda a: ((a.get("nombre_articulo") or "").upper(), int(a.get("id_art") or 0)))
            su["children"] = arts
        rb["children"] = ch
    return out


def _rollup_facturacion_unidades_detalle(detalle_tree: List[Dict[str, Any]]) -> None:
    """Recalcula facturación y unidades agregadas en subrubro y rubro desde las hojas (sin remitos por línea)."""
    for rb in detalle_tree:
        rb_fac = 0.0
        rb_uni = 0.0
        for sub in rb.get("children") or []:
            sf = su = 0.0
            for art in sub.get("children") or []:
                sf += float(art.get("facturacion") or 0)
                su += float(art.get("cantidades_vendidas") or 0)
            sub["facturacion"] = sf
            sub["cantidades_vendidas"] = su
            rb_fac += sf
            rb_uni += su
        rb["facturacion"] = rb_fac
        rb["cantidades_vendidas"] = rb_uni


_BO_DETAIL_KEYS = ("backorder_total", "bo_con_stock", "bo_con_ingreso", "bo_sin_stock")


def _rubro_tuple(rb: Dict[str, Any]) -> Tuple[int, str]:
    return (int(rb.get("codigo_rubro") or 0), (rb.get("nombre_rubro") or "").strip())


def _subrubro_tuple(sub: Dict[str, Any]) -> Tuple[int, str]:
    return (int(sub.get("id_subrubro") or 0), (sub.get("nombre_subrubro") or "").strip())


def _rollup_bo_en_detalle(detalle_tree: List[Dict[str, Any]]) -> None:
    """Suma métricas BO desde artículos hacia subrubro y rubro."""
    z = {k: 0.0 for k in _BO_DETAIL_KEYS}
    for rb in detalle_tree:
        rb_acc = dict(z)
        for sub in rb.get("children") or []:
            sub_acc = dict(z)
            for art in sub.get("children") or []:
                for k in _BO_DETAIL_KEYS:
                    sub_acc[k] += float(art.get(k) or 0)
            for k in _BO_DETAIL_KEYS:
                sub[k] = sub_acc[k]
                rb_acc[k] += sub_acc[k]
        for k in _BO_DETAIL_KEYS:
            rb[k] = rb_acc[k]


def _append_articulo_solo_bo(detalle_tree: List[Dict[str, Any]], id_art: int, b: Dict[str, Any]) -> None:
    """Agrega un artículo con ventas cero pero con BO (pedidos pendientes sin facturación en el período)."""
    if id_art <= 0:
        return
    cr = int(b.get("codigo_rubro") or 0)
    nr = (b.get("nombre_rubro") or "").strip() or "Sin rubro"
    isr = int(b.get("id_subrubro") or 0)
    nsr = (b.get("nombre_subrubro") or "").strip() or "Sin subrubro"
    nar = (b.get("nombre_articulo") or "").strip() or f"Artículo {id_art}"

    rb = None
    for r in detalle_tree:
        if _rubro_tuple(r) == (cr, nr):
            rb = r
            break
    if rb is None:
        rb = {
            "tipo": "rubro",
            "codigo_rubro": cr,
            "nombre_rubro": nr,
            "facturacion": 0.0,
            "cantidades_vendidas": 0.0,
            "children": [],
        }
        detalle_tree.append(rb)

    sub = None
    for s in rb.get("children") or []:
        if _subrubro_tuple(s) == (isr, nsr):
            sub = s
            break
    if sub is None:
        sub = {
            "tipo": "subrubro",
            "id_subrubro": isr,
            "nombre_subrubro": nsr,
            "facturacion": 0.0,
            "cantidades_vendidas": 0.0,
            "children": [],
        }
        rb["children"].append(sub)

    art: Dict[str, Any] = {
        "tipo": "articulo",
        "id_art": id_art,
        "nombre_articulo": nar,
        "facturacion": 0.0,
        "cantidades_vendidas": 0.0,
    }
    for k in _BO_DETAIL_KEYS:
        art[k] = float(b.get(k) or 0)
    sub["children"].append(art)


def _merge_bo_en_detalle_arbol(
    detalle_tree: List[Dict[str, Any]],
    bo_por_articulo: Dict[int, Dict[str, Any]],
) -> None:
    """
    Asigna BO por ID de artículo a cada fila de detalle y agrega artículos solo-BO.
    bo_por_articulo: id_art -> métricas + datos de rubro/subrubro/nombre para altas nuevas.
    """
    seen: Set[int] = set()
    for rb in detalle_tree:
        for sub in rb.get("children") or []:
            for art in sub.get("children") or []:
                iid = int(art.get("id_art") or 0)
                if iid > 0:
                    seen.add(iid)
                b = bo_por_articulo.get(iid) if iid > 0 else None
                if b:
                    for k in _BO_DETAIL_KEYS:
                        art[k] = float(b.get(k) or 0)
                else:
                    for k in _BO_DETAIL_KEYS:
                        art[k] = 0.0

    for iid, b in bo_por_articulo.items():
        if iid <= 0 or iid in seen:
            continue
        _append_articulo_solo_bo(detalle_tree, iid, b)


def run_ventas_objetivos_vs_bo(report: ReportDefinition, payload: Dict, user) -> QueryResult:
    svc = QueryRunnerService(user)
    filters = payload.get("filters", {}) or {}
    started_at = time.perf_counter()
    phase_started = started_at
    phase_ms: Dict[str, int] = {}

    def _mark_phase(name: str) -> None:
        nonlocal phase_started
        now = time.perf_counter()
        phase_ms[name] = int((now - phase_started) * 1000)
        phase_started = now

    fecha_inicio, fecha_fin = svc._resolve_period_dates(filters)
    if not fecha_inicio or not fecha_fin:
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
        )

    fi_fac_raw = filters.get("fecha_inicio_facturacion")
    ff_fac_raw = filters.get("fecha_fin_facturacion")
    fi_fac = str(fi_fac_raw).strip() if fi_fac_raw else ""
    ff_fac = str(ff_fac_raw).strip() if ff_fac_raw else ""
    if not fi_fac or not ff_fac:
        fi_fac, ff_fac = fecha_inicio, fecha_fin

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

    sucursales_ints, puntos_venta_ints = svc._parse_sucursales_pv(filters)

    depositos_incluidos = filters.get("depositos_incluidos", [])
    if isinstance(depositos_incluidos, str):
        depositos_incluidos = [depositos_incluidos] if depositos_incluidos else []
    elif not isinstance(depositos_incluidos, list):
        depositos_incluidos = []
    depositos_incluidos = [
        int(x) for x in depositos_incluidos if str(x).strip() and str(x).replace("-", "").isdigit()
    ]

    clientes_excluidos = svc._parse_clientes_excluidos(filters)
    vendedores_excluidos = svc._parse_vendedores_excluidos(filters)
    clientes_incluir = _parse_int_list(filters.get("clientes_incluir", []))
    vendedores_incluir = _parse_int_list(filters.get("vendedores_incluir", []))
    ordenar_por, orden_forma = _parse_sorting(filters)
    metric_key = _METRIC_ORDER_MAP[ordenar_por]

    # Reconciliación defensiva backend: si llega en ambos, prevalece "incluir".
    clientes_excluidos = [c for c in clientes_excluidos if int(c) not in set(clientes_incluir)]
    vendedores_excluidos = [v for v in vendedores_excluidos if int(v) not in set(vendedores_incluir)]
    _mark_phase("parse_filtros")

    lista_precio = filters.get("lista_precio")
    if lista_precio is None:
        lista_precio = 2
    try:
        lista_precio = int(lista_precio)
    except (TypeError, ValueError):
        lista_precio = 2
    if lista_precio not in range(0, 7):
        lista_precio = 2

    fecha_inicio_bo, fecha_fin_bo = parse_fecha_bo_yyyymmdd(fecha_inicio, fecha_fin)
    fi_fac_sql = _norm_yyyy_mm_dd(fi_fac)
    ff_fac_sql = _norm_yyyy_mm_dd(ff_fac)
    d_fac_ini = _parse_date_for_overlap(fi_fac)
    d_fac_fin = _parse_date_for_overlap(ff_fac)

    sd_where_excl = ""
    if depositos_incluidos:
        sd_where_excl = " WHERE id_deposito IN (" + ",".join(str(d) for d in depositos_incluidos) + ")"
    clientes_excl_bo = ""
    reservado_excl_clause = ""
    reservado_viaj_clause = ""
    if clientes_excluidos:
        clientes_excl_bo = " AND cp.Codigo NOT IN (" + ",".join(str(c) for c in clientes_excluidos) + ")"
        reservado_excl_clause = " AND cp_res.Codigo NOT IN (" + ",".join(str(c) for c in clientes_excluidos) + ")"
    if vendedores_excluidos:
        reservado_viaj_clause = " AND cl_res.CodViajante NOT IN (" + ",".join(str(x) for x in vendedores_excluidos) + ")"
    suc_bo_ph = ""
    if sucursales_ints:
        suc_bo_ph = " AND cp.CodSucursal IN (" + ",".join(["%s"] * len(sucursales_ints)) + ")"
    pv_bo_ph = ""
    if puntos_venta_ints:
        pv_bo_ph = " AND cp.id_pv IN (" + ",".join(["%s"] * len(puntos_venta_ints)) + ")"
    suc_res_inner = ""
    if sucursales_ints:
        suc_res_inner = " AND cp_res.CodSucursal IN (" + ",".join(str(x) for x in sucursales_ints) + ")"
    pv_res_inner = ""
    if puntos_venta_ints:
        pv_res_inner = " AND cp_res.id_pv IN (" + ",".join(str(x) for x in puntos_venta_ints) + ")"
    bo_estados = "('Pendiente')"

    obj_viaj_extra = ""
    if vendedores_excluidos:
        obj_viaj_extra = (
            " AND v.Codigo IN (SELECT cjx.Codigo FROM cliente cjx WHERE cjx.CodViajante NOT IN ("
            + ",".join(str(x) for x in vendedores_excluidos)
            + "))"
        )

    viaj_bo = ""
    if vendedores_excluidos:
        phvb = ",".join(["%s"] * len(vendedores_excluidos))
        viaj_bo = f" AND cl_bo.CodViajante NOT IN ({phvb})"

    notes: List[str] = []
    try:
        pool = get_mysql_pool()
        with pool.get_connection(str(base_empresa).strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SET SESSION max_execution_time = 90000")
            except Exception:
                pass

            # --- Facturación por cliente ---
            where_fac_cli = [
                "cc.Fecha >= %s",
                "cc.Fecha <= %s",
                "cc.Anulado = 'No'",
                "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')",
            ]
            params_fac_cli: List[Any] = [fi_fac_sql, ff_fac_sql]
            if sucursales_ints:
                phs = ",".join(["%s"] * len(sucursales_ints))
                where_fac_cli.append(f"cc.CodSucursal IN ({phs})")
                params_fac_cli.extend(sucursales_ints)
            if puntos_venta_ints:
                phpv = ",".join(["%s"] * len(puntos_venta_ints))
                where_fac_cli.append(f"cc.id_pv IN ({phpv})")
                params_fac_cli.extend(puntos_venta_ints)
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_fac_cli.append(f"cc.Codigo NOT IN ({ph})")
                params_fac_cli.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_fac_cli.append(f"cl.CodViajante NOT IN ({phv})")
                params_fac_cli.extend(vendedores_excluidos)
            where_fac_cli_s = " AND ".join(where_fac_cli)
            sql_fac_cli = f"""
                SELECT
                    cl.Codigo AS id_cliente,
                    COALESCE(MAX(cl.nombre_cliente), '') AS nombre_cliente,
                    SUM(CASE WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END)
                        - SUM(CASE WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END) AS sub_total,
                    COALESCE(MAX(cl.CodViajante), 0) AS cod_viajante,
                    COALESCE(MAX(v.Nombre), '') AS nombre_vendedor
                FROM cuentacliente cc
                INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
                LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante
                WHERE {where_fac_cli_s}
                GROUP BY cl.Codigo
            """
            cursor.execute(sql_fac_cli, params_fac_cli)
            fac_rows = cursor.fetchall()
            fact_map: Dict[int, Dict[str, Any]] = {}
            for r in fac_rows:
                cid = int(r[0])
                fact_map[cid] = {
                    "nombre_cliente": (r[1] or "").strip(),
                    "facturacion": float(r[2] or 0),
                    "cod_viajante": int(r[3] or 0),
                    "nombre_vendedor": (r[4] or "").strip(),
                }
            _mark_phase("query_facturacion")

            # --- Clientes con histórico de ventas (sin filtro de fechas ni sucursal en facturas) ---
            # Permite listar en el informe a quienes tienen movimiento en cuentacliente aunque en el
            # período solicitado la facturación sea 0 (las columnas de período quedarán en 0).
            where_hist_cli = [
                "cc.Anulado = 'No'",
                "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')",
            ]
            params_hist_cli: List[Any] = []
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_hist_cli.append(f"cl.Codigo NOT IN ({ph})")
                params_hist_cli.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_hist_cli.append(f"cl.CodViajante NOT IN ({phv})")
                params_hist_cli.extend(vendedores_excluidos)
            where_hist_cli_s = " AND ".join(where_hist_cli)
            sql_hist_cli = f"""
                SELECT cl.Codigo
                FROM cuentacliente cc
                INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
                LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante
                WHERE {where_hist_cli_s}
                GROUP BY cl.Codigo
                HAVING ABS(
                    SUM(CASE WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END)
                    - SUM(CASE WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END)
                ) > 0.000001
            """
            cursor.execute(sql_hist_cli, params_hist_cli)
            ids_con_historico_ventas = {int(r[0]) for r in cursor.fetchall() if r and r[0] is not None}
            _mark_phase("query_historico")

            # --- Remitos por cliente ---
            where_remitos = [
                "cp.Fecha >= %s",
                "cp.Fecha <= %s",
                "cp.TipoComprobante = 'REM'",
                "cp.Anulado = 'No'",
                "cp.Estado = 'Pendiente'",
            ]
            params_rem: List[Any] = [fi_fac_sql, ff_fac_sql]
            if sucursales_ints:
                phs = ",".join(["%s"] * len(sucursales_ints))
                where_remitos.append(f"cp.CodSucursal IN ({phs})")
                params_rem.extend(sucursales_ints)
            if puntos_venta_ints:
                phpv = ",".join(["%s"] * len(puntos_venta_ints))
                where_remitos.append(f"cp.id_pv IN ({phpv})")
                params_rem.extend(puntos_venta_ints)
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_remitos.append(f"cp.Codigo NOT IN ({ph})")
                params_rem.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_remitos.append(f"cl_rem.CodViajante NOT IN ({phv})")
                params_rem.extend(vendedores_excluidos)
            sql_rem_cli = f"""
                SELECT cp.Codigo, SUM(COALESCE(cp.SubtotalDesc, 0))
                FROM comp_ped cp
                INNER JOIN cliente cl_rem ON cl_rem.Codigo = cp.Codigo
                WHERE {" AND ".join(where_remitos)}
                GROUP BY cp.Codigo
            """
            cursor.execute(sql_rem_cli, params_rem)
            rem_map: Dict[int, float] = {}
            for r in cursor.fetchall():
                rem_map[int(r[0])] = float(r[1] or 0)
            _mark_phase("query_remitos")

            # --- Pedidos en armado por cliente (comp_ped PED; igual criterio que total-consolidado-operativo: sin filtro fecha) ---
            where_ped_arm = [
                "cp.TipoComprobante = 'PED'",
                "cp.Anulado = 'No'",
                "cp.Estado IN ('En preparación', 'Preparado')",
            ]
            params_ped: List[Any] = []
            if sucursales_ints:
                phs = ",".join(["%s"] * len(sucursales_ints))
                where_ped_arm.append(f"cp.CodSucursal IN ({phs})")
                params_ped.extend(sucursales_ints)
            if puntos_venta_ints:
                phpv = ",".join(["%s"] * len(puntos_venta_ints))
                where_ped_arm.append(f"cp.id_pv IN ({phpv})")
                params_ped.extend(puntos_venta_ints)
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_ped_arm.append(f"cp.Codigo NOT IN ({ph})")
                params_ped.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_ped_arm.append(f"cl_ped.CodViajante NOT IN ({phv})")
                params_ped.extend(vendedores_excluidos)
            sql_ped_arm = f"""
                SELECT cp.Codigo, SUM(COALESCE(cp.SubtotalDesc, 0))
                FROM comp_ped cp
                INNER JOIN cliente cl_ped ON cl_ped.Codigo = cp.Codigo
                WHERE {" AND ".join(where_ped_arm)}
                GROUP BY cp.Codigo
            """
            cursor.execute(sql_ped_arm, params_ped)
            ped_arm_map: Dict[int, float] = {}
            for r in cursor.fetchall():
                ped_arm_map[int(r[0])] = float(r[1] or 0)
            _mark_phase("query_pedidos_en_armado")

            # --- Unidades vendidas (stock + cuentacliente) ---
            ph_tc = ",".join(["%s"] * len(_TIPOS_FAC_NC))
            ph_st = ",".join(["%s"] * len(_STOCK_TIPO_COMP_VENTAS))
            where_uni = [
                "cc.Fecha >= %s",
                "cc.Fecha <= %s",
                "cc.Anulado = 'No'",
                "cc.CodigoMovimiento <> 0",
                f"cc.TipoComprobante IN ({ph_tc})",
                "st.Anulado = %s",
                f"st.TipoComp IN ({ph_st})",
            ]
            params_uni: List[Any] = [fi_fac_sql, ff_fac_sql] + list(_TIPOS_FAC_NC) + ["No"] + list(_STOCK_TIPO_COMP_VENTAS)
            if sucursales_ints:
                phs = ",".join(["%s"] * len(sucursales_ints))
                where_uni.append(f"cc.CodSucursal IN ({phs})")
                params_uni.extend(sucursales_ints)
            if puntos_venta_ints:
                phpv = ",".join(["%s"] * len(puntos_venta_ints))
                where_uni.append(f"cc.id_pv IN ({phpv})")
                params_uni.extend(puntos_venta_ints)
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_uni.append(f"cc.Codigo NOT IN ({ph})")
                params_uni.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_uni.append(f"cl_uni.CodViajante NOT IN ({phv})")
                params_uni.extend(vendedores_excluidos)
            sql_uni = f"""
                SELECT cc.Codigo,
                    SUM(CASE
                        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(st.Cantidad, 0)
                        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN -COALESCE(st.Cantidad, 0)
                        ELSE 0
                    END) AS unidades
                FROM stock st
                INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
                INNER JOIN cliente cl_uni ON cl_uni.Codigo = cc.Codigo
                WHERE {" AND ".join(where_uni)}
                GROUP BY cc.Codigo
            """
            cursor.execute(sql_uni, params_uni)
            uni_map: Dict[int, float] = {}
            for r in cursor.fetchall():
                uni_map[int(r[0])] = float(r[1] or 0)
            _mark_phase("query_unidades")

            # --- Detalle venta por rubro / subrubro / artículo (mismo rango y filtros que unidades) ---
            # Importe alineado a renglones stock.PrecioNetoxR (paridad ventas_netas / SPEC unidades).
            where_uni_s = " AND ".join(where_uni)
            sql_venta_por_art = f"""
                SELECT
                    cc.Codigo AS id_cliente,
                    COALESCE(art.CodigoRubro, 0) AS codigo_rubro,
                    COALESCE(MAX(ru.NombreRubro), '') AS nombre_rubro,
                    COALESCE(art.IDSubRubro, 0) AS id_subrubro,
                    COALESCE(MAX(sr.NombreSubRubro), '') AS nombre_subrubro,
                    COALESCE(art.IDArt, 0) AS id_art,
                    COALESCE(MAX(art.NombreArticulo), '') AS nombre_articulo,
                    SUM(CASE
                        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                            THEN COALESCE(st.PrecioNetoxR, 0)
                        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                            THEN -COALESCE(st.PrecioNetoxR, 0)
                        ELSE 0
                    END) AS factu_linea,
                    SUM(CASE
                        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                            THEN COALESCE(st.Cantidad, 0)
                        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                            THEN -COALESCE(st.Cantidad, 0)
                        ELSE 0
                    END) AS unidades_linea
                FROM stock st
                INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
                INNER JOIN cliente cl_uni ON cl_uni.Codigo = cc.Codigo
                LEFT JOIN articulo art ON art.IDArt = st.IDArt
                LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
                LEFT JOIN subrubro sr ON sr.IDSubRubro = art.IDSubRubro
                WHERE {where_uni_s}
                GROUP BY cc.Codigo, art.CodigoRubro, art.IDSubRubro, art.IDArt
                HAVING ABS(factu_linea) > 0.00001 OR ABS(unidades_linea) > 0.00001
            """
            cursor.execute(sql_venta_por_art, params_uni)
            detalle_flat_por_cliente: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
            for r in cursor.fetchall():
                cid = int(r[0])
                detalle_flat_por_cliente[cid].append(
                    {
                        "codigo_rubro": int(r[1] or 0),
                        "nombre_rubro": (r[2] or "").strip(),
                        "id_subrubro": int(r[3] or 0),
                        "nombre_subrubro": (r[4] or "").strip(),
                        "id_art": int(r[5] or 0),
                        "nombre_articulo": (r[6] or "").strip(),
                        "facturacion": float(r[7] or 0),
                        "cantidades_vendidas": float(r[8] or 0),
                    }
                )
            _mark_phase("query_detalle_ventas")

            # --- Objetivos (solape con rango facturación) ---
            objetivos_map: Dict[int, Decimal] = {}
            try:
                sql_obj = """
                    SELECT v1.Codigo, v1.objetivo
                    FROM viajantes_objetivos_ventas v1
                    INNER JOIN (
                        SELECT v.Codigo, MAX(v.id) AS max_id
                        FROM viajantes_objetivos_ventas v
                        LEFT JOIN viajantes_objetivos_periodo p ON p.id = v.id_periodo
                        WHERE (
                            (v.id_periodo IS NULL AND v.fecha_desde <= %s AND v.fecha_hasta >= %s)
                            OR (
                                v.id_periodo IS NOT NULL
                                AND p.id IS NOT NULL
                                AND COALESCE(p.anulado, 'No') = 'No'
                                AND p.fecha_desde <= %s AND p.fecha_hasta >= %s
                            )
                        )""" + obj_viaj_extra + """
                        GROUP BY v.Codigo
                    ) x ON x.Codigo = v1.Codigo AND x.max_id = v1.id
                """
                ff = d_fac_fin.isoformat()
                fi = d_fac_ini.isoformat()
                cursor.execute(sql_obj, [ff, fi, ff, fi])
                for r in cursor.fetchall():
                    objetivos_map[int(r[0])] = Decimal(str(r[1] or 0))
            except Exception as ex:
                logger.warning("Objetivos ventas: tabla o consulta no disponible: %s", ex)
                notes.append("No se pudieron leer objetivos (¿tabla viajantes_objetivos_ventas creada?).")
            _mark_phase("query_objetivos")

            # --- BO por cliente y artículo (misma lógica que BO agregado + prorrateo) ---
            sql_bo_by_client = f"""
                SELECT
                    cp.Codigo AS cod_cliente,
                    sp.IDArt AS id_art,
                    COALESCE(MAX(a.NombreArticulo), '') AS nombre_articulo,
                    COALESCE(MAX(a.CodigoRubro), 0) AS codigo_rubro,
                    COALESCE(MAX(ru.NombreRubro), '') AS nombre_rubro,
                    COALESCE(MAX(a.IDSubRubro), 0) AS id_subrubro,
                    COALESCE(MAX(sr.NombreSubRubro), '') AS nombre_subrubro,
                    SUM(sp.Cantidad) AS bo_qty,
                    SUM(sp.PrecioNetoxR) AS bo_importe,
                    COALESCE(sd.stock_total, 0) AS stock_actual,
                    COALESCE(reservado_sub.reservado, 0) AS stock_reservado,
                    GREATEST(0, COALESCE(sd.stock_total, 0) - COALESCE(reservado_sub.reservado, 0)) AS disponible,
                    GREATEST(0, COALESCE(oc_pendiente_sub.oc_pendiente, 0)) AS oc_pendiente
                FROM stockp sp
                INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                INNER JOIN cliente cl_bo ON cl_bo.Codigo = cp.Codigo
                LEFT JOIN articulo a ON a.IDArt = sp.IDArt
                LEFT JOIN rubro ru ON ru.CodigoRubro = a.CodigoRubro
                LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
                LEFT JOIN (
                    SELECT id_articulo, SUM(saldo) AS stock_total
                    FROM stock_deposito{sd_where_excl}
                    GROUP BY id_articulo
                ) sd ON sd.id_articulo = sp.IDArt
                LEFT JOIN (
                    SELECT sp_oc.IDArt AS id_articulo,
                        SUM(COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0))) AS oc_pendiente
                    FROM stockp sp_oc
                    INNER JOIN cuentaproveedor cp_oc ON cp_oc.CodigoMovimiento = sp_oc.CodigoMovimiento
                    WHERE cp_oc.TipoComprobante = 'OC'
                        AND (sp_oc.Comprobante = 'OC' OR sp_oc.Comprobante IS NULL)
                        AND cp_oc.Estado = 'Pendiente'
                        AND cp_oc.Anulado = 'No'
                        AND (sp_oc.anulado IS NULL OR sp_oc.anulado = 'No')
                        AND (COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0)) > 0)
                    GROUP BY sp_oc.IDArt
                ) oc_pendiente_sub ON oc_pendiente_sub.id_articulo = sp.IDArt
                LEFT JOIN (
                    SELECT sp_res.IDArt AS id_articulo,
                        SUM(COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0))) AS reservado
                    FROM stockp sp_res
                    INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
                    INNER JOIN cliente cl_res ON cl_res.Codigo = cp_res.Codigo
                    WHERE cp_res.TipoComprobante = 'PED'
                        AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
                        AND cp_res.Anulado = 'No'
                        AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
                        AND cp_res.Estado IN ('En preparación', 'Preparado')
                        AND (COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0){suc_res_inner}{pv_res_inner}{reservado_excl_clause}{reservado_viaj_clause}
                    GROUP BY sp_res.IDArt
                ) reservado_sub ON reservado_sub.id_articulo = sp.IDArt
                WHERE cp.TipoComprobante = 'PED'
                    AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
                    AND cp.Anulado = 'No'
                    AND (sp.anulado IS NULL OR sp.anulado = 'No')
                    AND cp.Estado IN {bo_estados}
                    AND sp.CodigoMovimiento IS NOT NULL
                    {suc_bo_ph}{pv_bo_ph}{viaj_bo}
                    AND sp.Fecha >= %s AND sp.Fecha <= %s{clientes_excl_bo}
                    AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
                GROUP BY cp.Codigo, sp.IDArt, sd.stock_total, oc_pendiente_sub.oc_pendiente, reservado_sub.reservado
                HAVING bo_qty > 0
            """
            _bo_params: List[Any] = []
            if sucursales_ints:
                _bo_params.extend(sucursales_ints)
            if puntos_venta_ints:
                _bo_params.extend(puntos_venta_ints)
            if vendedores_excluidos:
                _bo_params.extend(vendedores_excluidos)
            _bo_params.extend([fecha_inicio_bo, fecha_fin_bo])
            cursor.execute(sql_bo_by_client, _bo_params)
            bo_cli_agg: Dict[int, Dict[str, float]] = defaultdict(
                lambda: {"bo_total": 0.0, "con_stock": 0.0, "con_ingreso": 0.0, "sin_stock": 0.0}
            )
            bo_art_detail: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(dict)
            for row in cursor.fetchall():
                cod_c = int(row[0])
                id_art = int(row[1] or 0)
                nombre_art = (row[2] or "").strip()
                cod_r = int(row[3] or 0)
                nom_r = (row[4] or "").strip() or "Sin rubro"
                id_sr = int(row[5] or 0)
                nom_sr = (row[6] or "").strip() or "Sin subrubro"
                bo_qty = float(row[7] or 0)
                bo_importe = float(row[8] or 0)
                stock_actual = float(row[9] or 0)
                stock_reservado = float(row[10] or 0)
                disponible = float(row[11] or 0)
                oc_pendiente = float(row[12] or 0)
                faltante_reservado = max(0.0, stock_reservado - stock_actual)
                oc_para_reservado = min(oc_pendiente, faltante_reservado)
                oc_restante_bo = max(0.0, oc_pendiente - oc_para_reservado)
                con_stock_qty = min(bo_qty, disponible)
                rest = bo_qty - con_stock_qty
                con_ingreso_qty = min(rest, oc_restante_bo)
                sin_stock_qty = rest - con_ingreso_qty
                if bo_qty > 0:
                    csi = bo_importe * (con_stock_qty / bo_qty)
                    cii = bo_importe * (con_ingreso_qty / bo_qty)
                    ssi = bo_importe * (sin_stock_qty / bo_qty)
                else:
                    csi = cii = ssi = 0.0
                agg_c = bo_cli_agg[cod_c]
                agg_c["bo_total"] += bo_importe
                agg_c["con_stock"] += csi
                agg_c["con_ingreso"] += cii
                agg_c["sin_stock"] += ssi

                if id_art <= 0:
                    continue
                slot = bo_art_detail[cod_c].setdefault(
                    id_art,
                    {
                        "nombre_articulo": nombre_art,
                        "codigo_rubro": cod_r,
                        "nombre_rubro": nom_r,
                        "id_subrubro": id_sr,
                        "nombre_subrubro": nom_sr,
                        "backorder_total": 0.0,
                        "bo_con_stock": 0.0,
                        "bo_con_ingreso": 0.0,
                        "bo_sin_stock": 0.0,
                    },
                )
                slot["backorder_total"] += bo_importe
                slot["bo_con_stock"] += csi
                slot["bo_con_ingreso"] += cii
                slot["bo_sin_stock"] += ssi
                if nombre_art:
                    slot["nombre_articulo"] = nombre_art
            _mark_phase("query_backorder")

            all_ids = sorted(
                set(fact_map.keys())
                | ids_con_historico_ventas
                | set(rem_map.keys())
                | set(uni_map.keys())
                | set(bo_cli_agg.keys())
                | set(objetivos_map.keys())
            )
            if clientes_incluir:
                all_ids = [cid for cid in all_ids if cid in set(clientes_incluir)]
            master: Dict[int, Dict[str, Any]] = {}
            if all_ids:
                ph = ",".join(["%s"] * len(all_ids))
                cursor.execute(
                    f"""
                    SELECT cl.Codigo, COALESCE(cl.nombre_cliente, ''), COALESCE(cl.CodViajante, 0), COALESCE(v.Nombre, '')
                    FROM cliente cl
                    LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante
                    WHERE cl.Codigo IN ({ph})
                    """,
                    all_ids,
                )
                for r in cursor.fetchall():
                    master[int(r[0])] = {
                        "nombre_cliente": (r[1] or "").strip(),
                        "cod_viajante": int(r[2] or 0),
                        "nombre_vendedor": (r[3] or "").strip(),
                    }
            _mark_phase("query_master_clientes")

            rows_out: List[Dict[str, Any]] = []
            for cid in all_ids:
                m = master.get(cid)
                if not m or m["cod_viajante"] == 0:
                    continue
                nom_c = m["nombre_cliente"]
                cv = m["cod_viajante"]
                if vendedores_incluir and cv not in set(vendedores_incluir):
                    continue
                if vendedores_excluidos and cv in vendedores_excluidos:
                    continue
                nv = m["nombre_vendedor"]
                fm = fact_map.get(cid)

                fac = float(fm["facturacion"]) if fm else 0.0
                rem = rem_map.get(cid, 0.0)
                ped_arm = ped_arm_map.get(cid, 0.0)
                uni = uni_map.get(cid, 0.0)
                bo = bo_cli_agg.get(cid, {"bo_total": 0.0, "con_stock": 0.0, "con_ingreso": 0.0, "sin_stock": 0.0})
                obj = float(objetivos_map.get(cid, Decimal("0")))
                total_fr = float(calcular_total_consolidado_objetivos(fac, rem, ped_arm))
                falta = float(calcular_falta(obj, fac, rem, ped_arm))

                rows_out.append(
                    {
                        "codigo_cliente": cid,
                        "nombre_cliente": nom_c,
                        "cod_viajante": cv,
                        "nombre_vendedor": nv,
                        "objetivo": obj,
                        "facturacion": fac,
                        "remitos": rem,
                        "pedidos_en_armado": ped_arm,
                        "total": total_fr,
                        "falta": falta,
                        "cantidades_vendidas": uni,
                        "backorder_total": bo["bo_total"],
                        "bo_con_stock": bo["con_stock"],
                        "bo_con_ingreso": bo["con_ingreso"],
                        "bo_sin_stock": bo["sin_stock"],
                    }
                )

            # Árbol vendedor -> estado_compra -> clientes
            grupos: Dict[int, Dict[str, Any]] = {}
            for row in rows_out:
                cv = row["cod_viajante"]
                if cv not in grupos:
                    grupos[cv] = {
                        "tipo": "vendedor",
                        "cod_viajante": cv,
                        "nombre_vendedor": row["nombre_vendedor"] or f"Vendedor {cv}",
                        "children": [],
                        "objetivo": 0.0,
                        "facturacion": 0.0,
                        "remitos": 0.0,
                        "pedidos_en_armado": 0.0,
                        "total": 0.0,
                        "falta": 0.0,
                        "cantidades_vendidas": 0.0,
                        "backorder_total": 0.0,
                        "bo_con_stock": 0.0,
                        "bo_con_ingreso": 0.0,
                        "bo_sin_stock": 0.0,
                        "total_clientes": 0,
                        "total_clientes_con_compra": 0,
                        "total_clientes_sin_compra": 0,
                    }
                g = grupos[cv]
                cid = int(row.get("codigo_cliente") or 0)
                vd_tree = _nest_venta_detalle_rubro_subrubro_articulo(detalle_flat_por_cliente.get(cid, []))
                _merge_bo_en_detalle_arbol(vd_tree, bo_art_detail.get(cid, {}))
                _rollup_bo_en_detalle(vd_tree)
                _rollup_facturacion_unidades_detalle(vd_tree)
                vd = _sort_nested_detalle(vd_tree, metric_key=metric_key, direction=orden_forma)
                total_cli = float(row.get("total") or 0)
                estado_compra = "con_compra" if abs(total_cli) > 0.000001 else "sin_compra"
                if not any(ch.get("tipo") == "estado_compra" and ch.get("estado_compra") == estado_compra for ch in g["children"]):
                    g["children"].append(
                        {
                            "tipo": "estado_compra",
                            "estado_compra": estado_compra,
                            "nombre": "Con compra" if estado_compra == "con_compra" else "Sin compra",
                            "children": [],
                            "objetivo": 0.0,
                            "facturacion": 0.0,
                            "remitos": 0.0,
                            "pedidos_en_armado": 0.0,
                            "total": 0.0,
                            "falta": 0.0,
                            "cantidades_vendidas": 0.0,
                            "backorder_total": 0.0,
                            "bo_con_stock": 0.0,
                            "bo_con_ingreso": 0.0,
                            "bo_sin_stock": 0.0,
                            "total_clientes": 0,
                        }
                    )
                estado_node = next(
                    ch for ch in g["children"] if ch.get("tipo") == "estado_compra" and ch.get("estado_compra") == estado_compra
                )
                ch = {**row, "tipo": "cliente", "venta_detalle": vd, "estado_compra": estado_compra}
                estado_node["children"].append(ch)
                estado_node["total_clientes"] = int(estado_node.get("total_clientes") or 0) + 1
                g["total_clientes"] = int(g.get("total_clientes") or 0) + 1
                if estado_compra == "con_compra":
                    g["total_clientes_con_compra"] = int(g.get("total_clientes_con_compra") or 0) + 1
                else:
                    g["total_clientes_sin_compra"] = int(g.get("total_clientes_sin_compra") or 0) + 1
                for k in (
                    "objetivo",
                    "facturacion",
                    "remitos",
                    "pedidos_en_armado",
                    "total",
                    "falta",
                    "cantidades_vendidas",
                    "backorder_total",
                    "bo_con_stock",
                    "bo_con_ingreso",
                    "bo_sin_stock",
                ):
                    g[k] = float(g.get(k, 0) or 0) + float(row.get(k, 0) or 0)
                    estado_node[k] = float(estado_node.get(k, 0) or 0) + float(row.get(k, 0) or 0)

            # Orden recursivo por métrica + desempate alfabético.
            for g in grupos.values():
                g["children"].sort(
                    key=lambda x: (
                        _sort_scalar(_group_metric(x, metric_key), orden_forma),
                        (x.get("nombre") or "").upper(),
                        0 if (x.get("estado_compra") or "") == "con_compra" else 1,
                    )
                )
                for estado in g["children"]:
                    estado["children"].sort(
                        key=lambda x: (
                            _sort_scalar(_group_metric(x, metric_key), orden_forma),
                            (x.get("nombre_cliente") or "").upper(),
                            int(x.get("codigo_cliente") or 0),
                        )
                    )

            # Nivel vendedor con el mismo criterio de ordenamiento.
            arbol = sorted(
                grupos.values(),
                key=lambda x: (
                    _sort_scalar(_group_metric(x, metric_key), orden_forma),
                    (x.get("nombre_vendedor") or "").upper(),
                    int(x.get("cod_viajante") or 0),
                ),
            )

            rows_ordered: List[Dict[str, Any]] = []
            for g in arbol:
                for estado in g["children"]:
                    for ch in estado.get("children") or []:
                        rows_ordered.append({k: v for k, v in ch.items() if k not in ("tipo", "venta_detalle")})
            rows_out = rows_ordered
            _mark_phase("armado_jerarquia")

            tot = {
                "objetivo": sum(float(x["objetivo"]) for x in rows_out),
                "facturacion": sum(float(x["facturacion"]) for x in rows_out),
                "remitos": sum(float(x["remitos"]) for x in rows_out),
                "pedidos_en_armado": sum(float(x["pedidos_en_armado"]) for x in rows_out),
                "total": sum(float(x["total"]) for x in rows_out),
                "falta": sum(float(x["falta"]) for x in rows_out),
                "cantidades_vendidas": sum(float(x["cantidades_vendidas"]) for x in rows_out),
                "backorder_total": sum(float(x["backorder_total"]) for x in rows_out),
                "bo_con_stock": sum(float(x["bo_con_stock"]) for x in rows_out),
                "bo_con_ingreso": sum(float(x["bo_con_ingreso"]) for x in rows_out),
                "bo_sin_stock": sum(float(x["bo_sin_stock"]) for x in rows_out),
                "total_clientes": len(rows_out),
                "total_vendedores": len(arbol),
            }

            filters_applied = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "fecha_inicio_facturacion": fi_fac_sql,
                "fecha_fin_facturacion": ff_fac_sql,
                "fecha_inicio_bo": fecha_inicio_bo,
                "fecha_fin_bo": fecha_fin_bo,
                "sucursales": sucursales_ints,
                "punto_venta": puntos_venta_ints,
                "depositos_incluidos": depositos_incluidos,
                "clientes_excluidos": clientes_excluidos,
                "vendedores_excluidos": vendedores_excluidos,
                "clientes_incluir": clientes_incluir,
                "vendedores_incluir": vendedores_incluir,
                "lista_precio": lista_precio,
                "lista_precio_label": _label_lista_precio(lista_precio),
                "ordenar_por": ordenar_por,
                "orden_forma": orden_forma,
            }
            filters_applied["performance_phase_ms"] = phase_ms
            filters_applied["performance_total_ms"] = int((time.perf_counter() - started_at) * 1000)
            notes.insert(
                0,
                f"Facturación/remitos: {fi_fac_sql} a {ff_fac_sql}. Backorder: {fecha_inicio_bo} a {fecha_fin_bo}.",
            )
            notes.append(
                "Pedidos en armado: importe de PED en estado En preparación/Preparado, sin filtro por fechas "
                "(misma semántica que el KPI del reporte total-consolidado-operativo)."
            )
            if puntos_venta_ints:
                notes.append(
                    f"Puntos de venta filtrados ({len(puntos_venta_ints)}): facturación, remitos, pedidos en armado, "
                    "unidades/detalle y cabeceras BO usan cc.id_pv / cp.id_pv como en total-consolidado-operativo."
                )
            notes.append(
                f"Clientes en grilla: {len(rows_out)} "
                "(unión de histórico de ventas en cuentacliente —sin acotar por ventana—, "
                "movimiento en el período, objetivos vigentes, remitos/BO/unidades según filtros)."
            )

            extra = {
                "tabs": {
                    "objetivos_jerarquia": arbol,
                    "objetivos_filas": rows_out,
                },
            }
            cursor.close()

        _persist_perf_log(
            report=report,
            user=user,
            filters_snapshot=filters_applied,
            phase_ms=phase_ms,
            total_ms=int((time.perf_counter() - started_at) * 1000),
            status="success",
            note=f"Ejecución OK para {report.slug}",
        )
        return QueryResult(
            meta={
                "slug": report.slug,
                "name": report.name,
                "category": report.category,
                "version": report.version,
                "extra": extra,
                "filters_applied": _filters_applied_para_respuesta(filters_applied, user),
            },
            data=rows_out,
            totals=tot,
            notes=notes,
        )
    except Exception as e:
        logger.exception("ventas_objetivos_vs_bo: %s", e)
        try:
            _persist_perf_log(
                report=report,
                user=user,
                filters_snapshot={"error": str(e), "filters": filters},
                phase_ms=phase_ms,
                total_ms=int((time.perf_counter() - started_at) * 1000),
                status="error",
                note=f"Error en ejecución: {e}",
            )
        except Exception:
            logger.exception("No se pudo persistir log de error de performance")
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=[f"Error al ejecutar el informe: {e}"],
        )
