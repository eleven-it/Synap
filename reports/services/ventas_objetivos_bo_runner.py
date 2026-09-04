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
from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.ajustes_sin_mercaderia import (
    CODIGO_SINTETICO_AJUSTES,
    NOMBRE_AJUSTES,
    NOMBRE_FA_NC_CABECERA,
    NOTA_AJUSTES_INCLUIDOS,
    NOTA_AJUSTES_OMITIDOS_CATALOGO,
    TIPOS_COMP_VENTA,
    consultar_ajustes_sin_mercaderia,
    pin_ajustes_al_final,
)
from reports.services.connection_pool import get_mysql_pool
from reports.services.ventas_marcas_mensual_rules import sql_signo_imp_post_pie_expr
from reports.services.objetivos_ventas_contract import (
    calcular_falta,
    calcular_total_consolidado_objetivos,
)
from reports.services.query_runner import QueryResult, QueryRunnerService, parse_fecha_bo_yyyymmdd
from ventas.services.objetivos_mysql import (
    agrupar_jerarquia_informe_arbol_org,
    alcance_objetivos_cod_viajante,
    ctx_desde_runner,
)

logger = logging.getLogger(__name__)


def _sql_in_viajantes(alias: str, codigos: List[int]) -> Tuple[str, List[int]]:
    if not codigos:
        return "", []
    ph = ",".join(["%s"] * len(codigos))
    return f" AND {alias}.CodViajante IN ({ph})", list(codigos)


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
    "facturacion_periodo": "facturacion",
    "unidades_periodo": "cantidades_vendidas",
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


def _vo_sql_filtros_articulo(
    alias_art: str,
    *,
    rubros_incluidos: List[int] | None = None,
    rubros_excluidos: List[int] | None = None,
    subrubros_incluidos: List[int] | None = None,
    subrubros_excluidos: List[int] | None = None,
    marcas_incluidos: List[int] | None = None,
    marcas_excluidos: List[int] | None = None,
) -> Tuple[str, List[Any]]:
    """Fragmento ``AND ...`` para limitar líneas por rubro/subrubro/marca (incluir y excluir)."""
    rubros_incluidos = rubros_incluidos or []
    rubros_excluidos = rubros_excluidos or []
    subrubros_incluidos = subrubros_incluidos or []
    subrubros_excluidos = subrubros_excluidos or []
    marcas_incluidos = marcas_incluidos or []
    marcas_excluidos = marcas_excluidos or []
    parts: List[str] = []
    params: List[Any] = []
    if rubros_incluidos:
        ph = ",".join(["%s"] * len(rubros_incluidos))
        parts.append(f"{alias_art}.CodigoRubro IN ({ph})")
        params.extend(rubros_incluidos)
    if rubros_excluidos:
        ph = ",".join(["%s"] * len(rubros_excluidos))
        parts.append(f"{alias_art}.CodigoRubro NOT IN ({ph})")
        params.extend(rubros_excluidos)
    if subrubros_incluidos:
        ph = ",".join(["%s"] * len(subrubros_incluidos))
        parts.append(f"{alias_art}.IDSubRubro IN ({ph})")
        params.extend(subrubros_incluidos)
    if subrubros_excluidos:
        ph = ",".join(["%s"] * len(subrubros_excluidos))
        parts.append(f"{alias_art}.IDSubRubro NOT IN ({ph})")
        params.extend(subrubros_excluidos)
    if marcas_incluidos:
        ph = ",".join(["%s"] * len(marcas_incluidos))
        parts.append(f"{alias_art}.CodigoMarca IN ({ph})")
        params.extend(marcas_incluidos)
    if marcas_excluidos:
        ph = ",".join(["%s"] * len(marcas_excluidos))
        parts.append(f"{alias_art}.CodigoMarca NOT IN ({ph})")
        params.extend(marcas_excluidos)
    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def _vo_sql_filtros_rubro_subrubro(
    alias_art: str,
    rubros_incluidos: List[int],
    subrubros_incluidos: List[int],
) -> Tuple[str, List[Any]]:
    """Paridad VO: solo rubro/subrubro a incluir."""
    return _vo_sql_filtros_articulo(
        alias_art,
        rubros_incluidos=rubros_incluidos,
        subrubros_incluidos=subrubros_incluidos,
    )


# Fila sintética en el árbol de detalle cuando la facturación de cabecera (cuentacliente)
# no coincide con la suma de renglones stock+artículo en el período.
_ID_ART_FACTURACION_SIN_DESGLOSE = -900000001
# Rubro sintético: código negativo reservado (evita colisión con rubro real CodigoRubro=0 en la UI VO).
_CODIGO_RUBRO_RESIDUAL_FACTURACION = -900000000


def _sum_facturacion_unidades_hojas_detalle(detalle_tree: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Suma facturación y unidades solo en nodos hoja artículo (excluye la fila residual si existiera)."""
    tf = 0.0
    tu = 0.0
    for rb in detalle_tree:
        for sub in rb.get("children") or []:
            for art in sub.get("children") or []:
                if int(art.get("id_art") or 0) == _ID_ART_FACTURACION_SIN_DESGLOSE:
                    continue
                tf += float(art.get("facturacion") or 0)
                tu += float(art.get("cantidades_vendidas") or 0)
    return tf, tu


def _append_articulo_residual_facturacion(
    detalle_tree: List[Dict[str, Any]],
    delta_fac: float,
    delta_uni: float,
) -> None:
    """Agrupa la diferencia cabecera vs renglones bajo un rubro explícito para que el usuario pueda desplegar el árbol."""
    if abs(delta_fac) < 0.02 and abs(delta_uni) < 0.02:
        return
    cr = _CODIGO_RUBRO_RESIDUAL_FACTURACION
    nr = "Facturación sin desglose por artículo"
    isr = 0
    nsr = "—"
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
        "id_art": _ID_ART_FACTURACION_SIN_DESGLOSE,
        "nombre_articulo": "Importe en cabecera sin líneas de stock con artículo en el período",
        "facturacion": float(delta_fac),
        "cantidades_vendidas": float(delta_uni),
    }
    for k in _BO_DETAIL_KEYS:
        art[k] = 0.0
    art["remitos_lineas"] = 0.0
    art["pedidos_armado_lineas"] = 0.0
    sub["children"].append(art)


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
    Los importes de **remitos** y **pedidos en armado** por artículo (`remitos_lineas`, `pedidos_armado_lineas`)
    se fusionan después con `_merge_rem_ped_lineas_en_detalle_arbol` (líneas `stockp`, ver verify del proyecto).
    El BO se fusiona con `_merge_bo_en_detalle_arbol`; las agregaciones se recalculan con rollups y
    `_rollup_facturacion_unidades_detalle` tras incorporar artículos solo-BO o solo-REM/PED.
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


def _rollup_rem_ped_lineas_en_detalle(detalle_tree: List[Dict[str, Any]]) -> None:
    """Suma remitos_lineas y pedidos_armado_lineas desde artículos hacia subrubro y rubro."""
    for rb in detalle_tree:
        rb_r = 0.0
        rb_p = 0.0
        for sub in rb.get("children") or []:
            su_r = 0.0
            su_p = 0.0
            for art in sub.get("children") or []:
                su_r += float(art.get("remitos_lineas") or 0)
                su_p += float(art.get("pedidos_armado_lineas") or 0)
            sub["remitos_lineas"] = su_r
            sub["pedidos_armado_lineas"] = su_p
            rb_r += su_r
            rb_p += su_p
        rb["remitos_lineas"] = rb_r
        rb["pedidos_armado_lineas"] = rb_p


def _append_articulo_solo_rem_ped_lineas(
    detalle_tree: List[Dict[str, Any]],
    id_art: int,
    rem_v: float,
    ped_v: float,
    nombre_articulo: str,
    cod_r: int,
    nom_r: str,
    id_sr: int,
    nom_sr: str,
) -> None:
    """Artículo solo con importes REM/PED por líneas (sin facturación ni BO en el período)."""
    if id_art <= 0:
        return
    cr = int(cod_r or 0)
    nr = (nom_r or "").strip() or "Sin rubro"
    isr = int(id_sr or 0)
    nsr = (nom_sr or "").strip() or "Sin subrubro"
    nar = (nombre_articulo or "").strip() or f"Artículo {id_art}"

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
            "remitos_lineas": 0.0,
            "pedidos_armado_lineas": 0.0,
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
            "remitos_lineas": 0.0,
            "pedidos_armado_lineas": 0.0,
            "children": [],
        }
        rb["children"].append(sub)

    art: Dict[str, Any] = {
        "tipo": "articulo",
        "id_art": id_art,
        "nombre_articulo": nar,
        "facturacion": 0.0,
        "cantidades_vendidas": 0.0,
        "remitos_lineas": float(rem_v or 0),
        "pedidos_armado_lineas": float(ped_v or 0),
    }
    for k in _BO_DETAIL_KEYS:
        art[k] = 0.0
    sub["children"].append(art)


def _merge_rem_ped_lineas_en_detalle_arbol(
    detalle_tree: List[Dict[str, Any]],
    rem_por_art: Dict[int, Dict[str, Any]],
    ped_por_art: Dict[int, Dict[str, Any]],
) -> None:
    """
    Asigna remitos_lineas / pedidos_armado_lineas por ID de artículo y agrega artículos solo-REM/PED.
    rem_por_art / ped_por_art: id_art -> dict con importes y metadatos de rubro (como bo_art_detail).
    """
    combined: Dict[int, Dict[str, Any]] = {}
    for iid, r in rem_por_art.items():
        ii = int(iid or 0)
        if ii <= 0:
            continue
        slot = combined.setdefault(
            ii,
            {
                "remitos_lineas": 0.0,
                "pedidos_armado_lineas": 0.0,
                "nombre_articulo": "",
                "codigo_rubro": 0,
                "nombre_rubro": "",
                "id_subrubro": 0,
                "nombre_subrubro": "",
            },
        )
        slot["remitos_lineas"] = float(r.get("remitos_lineas") or 0)
        if (r.get("nombre_articulo") or "").strip():
            slot["nombre_articulo"] = (r.get("nombre_articulo") or "").strip()
        slot["codigo_rubro"] = int(r.get("codigo_rubro") or slot["codigo_rubro"] or 0)
        slot["nombre_rubro"] = (r.get("nombre_rubro") or "").strip() or slot["nombre_rubro"]
        slot["id_subrubro"] = int(r.get("id_subrubro") or slot["id_subrubro"] or 0)
        slot["nombre_subrubro"] = (r.get("nombre_subrubro") or "").strip() or slot["nombre_subrubro"]
    for iid, p in ped_por_art.items():
        ii = int(iid or 0)
        if ii <= 0:
            continue
        slot = combined.setdefault(
            ii,
            {
                "remitos_lineas": 0.0,
                "pedidos_armado_lineas": 0.0,
                "nombre_articulo": "",
                "codigo_rubro": 0,
                "nombre_rubro": "",
                "id_subrubro": 0,
                "nombre_subrubro": "",
            },
        )
        slot["pedidos_armado_lineas"] = float(p.get("pedidos_armado_lineas") or 0)
        if (p.get("nombre_articulo") or "").strip() and not (slot.get("nombre_articulo") or "").strip():
            slot["nombre_articulo"] = (p.get("nombre_articulo") or "").strip()
        if int(p.get("codigo_rubro") or 0) and not slot.get("codigo_rubro"):
            slot["codigo_rubro"] = int(p.get("codigo_rubro") or 0)
        if (p.get("nombre_rubro") or "").strip() and not (slot.get("nombre_rubro") or "").strip():
            slot["nombre_rubro"] = (p.get("nombre_rubro") or "").strip()
        if int(p.get("id_subrubro") or 0) and not slot.get("id_subrubro"):
            slot["id_subrubro"] = int(p.get("id_subrubro") or 0)
        if (p.get("nombre_subrubro") or "").strip() and not (slot.get("nombre_subrubro") or "").strip():
            slot["nombre_subrubro"] = (p.get("nombre_subrubro") or "").strip()

    seen: Set[int] = set()
    for rb in detalle_tree:
        for sub in rb.get("children") or []:
            for art in sub.get("children") or []:
                iid = int(art.get("id_art") or 0)
                if iid > 0:
                    seen.add(iid)
                c = combined.get(iid) if iid > 0 else None
                if c:
                    art["remitos_lineas"] = float(c.get("remitos_lineas") or 0)
                    art["pedidos_armado_lineas"] = float(c.get("pedidos_armado_lineas") or 0)
                else:
                    art["remitos_lineas"] = float(art.get("remitos_lineas") or 0)
                    art["pedidos_armado_lineas"] = float(art.get("pedidos_armado_lineas") or 0)

    for iid, c in combined.items():
        if iid <= 0 or iid in seen:
            continue
        if abs(float(c.get("remitos_lineas") or 0)) < 1e-9 and abs(float(c.get("pedidos_armado_lineas") or 0)) < 1e-9:
            continue
        _append_articulo_solo_rem_ped_lineas(
            detalle_tree,
            iid,
            float(c.get("remitos_lineas") or 0),
            float(c.get("pedidos_armado_lineas") or 0),
            str(c.get("nombre_articulo") or ""),
            int(c.get("codigo_rubro") or 0),
            str(c.get("nombre_rubro") or ""),
            int(c.get("id_subrubro") or 0),
            str(c.get("nombre_subrubro") or ""),
        )


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


_NOMBRE_SIN_PROVEEDOR = "Sin proveedor"


def _nombre_proveedor_display(codigo_proveedor: int, nombre_proveedor: str) -> str:
    cod = int(codigo_proveedor or 0)
    if cod <= 0:
        return _NOMBRE_SIN_PROVEEDOR
    nombre = (nombre_proveedor or "").strip()
    return nombre or f"Proveedor {cod}"


def _nest_articulo_proveedor_cliente(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa filas planas en árbol artículo → proveedor → cliente."""
    articulos: Dict[int, Dict[str, Any]] = {}
    for rw in filas:
        id_art = int(rw.get("id_art") or 0)
        if id_art <= 0:
            continue
        nombre_art = (rw.get("nombre_articulo") or "").strip() or "Sin artículo"
        cod_prov = int(rw.get("codigo_proveedor") or 0)
        nombre_prov = _nombre_proveedor_display(cod_prov, rw.get("nombre_proveedor") or "")
        cod_cli = int(rw.get("codigo_cliente") or 0)
        nombre_cli = (rw.get("nombre_cliente") or "").strip() or f"Cliente {cod_cli}"
        fac = float(rw.get("facturacion") or 0)
        uni = float(rw.get("cantidades_vendidas") or 0)

        art = articulos.get(id_art)
        if not art:
            art = {
                "tipo": "articulo",
                "id_art": id_art,
                "nombre_articulo": nombre_art,
                "children": [],
                "cantidades_vendidas": 0.0,
                "facturacion": 0.0,
                "_prov": {},
            }
            articulos[id_art] = art
        art["cantidades_vendidas"] += uni
        art["facturacion"] += fac

        pk = (cod_prov, nombre_prov)
        prov_map: Dict[Tuple[int, str], Dict[str, Any]] = art["_prov"]
        prov = prov_map.get(pk)
        if not prov:
            prov = {
                "tipo": "proveedor",
                "codigo_proveedor": cod_prov,
                "nombre_proveedor": nombre_prov,
                "children": [],
                "cantidades_vendidas": 0.0,
                "facturacion": 0.0,
                "_cli": {},
            }
            prov_map[pk] = prov
        prov["cantidades_vendidas"] += uni
        prov["facturacion"] += fac

        cli_map: Dict[int, Dict[str, Any]] = prov["_cli"]
        cli = cli_map.get(cod_cli)
        if not cli:
            cli = {
                "tipo": "cliente",
                "codigo_cliente": cod_cli,
                "nombre_cliente": nombre_cli,
                "cantidades_vendidas": 0.0,
                "facturacion": 0.0,
            }
            cli_map[cod_cli] = cli
        cli["cantidades_vendidas"] += uni
        cli["facturacion"] += fac

    out: List[Dict[str, Any]] = []
    for art in articulos.values():
        prov_map = art.pop("_prov", {})
        provs: List[Dict[str, Any]] = []
        for prov in prov_map.values():
            cli_map = prov.pop("_cli", {})
            prov["children"] = sorted(
                cli_map.values(),
                key=lambda x: (
                    (x.get("nombre_cliente") or "").upper(),
                    int(x.get("codigo_cliente") or 0),
                ),
            )
            provs.append(prov)
        art["children"] = sorted(
            provs,
            key=lambda x: (
                (x.get("nombre_proveedor") or "").upper(),
                int(x.get("codigo_proveedor") or 0),
            ),
        )
        out.append(art)
    out.sort(key=lambda x: ((x.get("nombre_articulo") or "").upper(), int(x.get("id_art") or 0)))
    return out


def _group_metric_articulo(node: Dict[str, Any], metric_key: str) -> float:
    return float(node.get(metric_key) or 0)


def _sort_scalar_articulo(value: float, direction: str) -> float:
    mult = _ORDER_DIRECTION_MAP.get(direction, -1)
    return float(value) * float(mult)


def _sort_arbol_ventas_por_articulo(
    arbol: List[Dict[str, Any]], metric_key: str, direction: str
) -> List[Dict[str, Any]]:
    for art in arbol:
        for prov in art.get("children") or []:
            prov["children"].sort(
                key=lambda x: (
                    _sort_scalar_articulo(_group_metric_articulo(x, metric_key), direction),
                    (x.get("nombre_cliente") or "").upper(),
                    int(x.get("codigo_cliente") or 0),
                )
            )
        art["children"].sort(
            key=lambda x: (
                _sort_scalar_articulo(_group_metric_articulo(x, metric_key), direction),
                (x.get("nombre_proveedor") or "").upper(),
                int(x.get("codigo_proveedor") or 0),
            )
        )
    arbol.sort(
        key=lambda x: (
            _sort_scalar_articulo(_group_metric_articulo(x, metric_key), direction),
            (x.get("nombre_articulo") or "").upper(),
            int(x.get("id_art") or 0),
        )
    )
    return arbol


def _flatten_filas_ventas_por_articulo(arbol: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for art in arbol:
        for prov in art.get("children") or []:
            for cli in prov.get("children") or []:
                rows.append(
                    {
                        "id_art": art.get("id_art"),
                        "nombre_articulo": art.get("nombre_articulo"),
                        "codigo_proveedor": prov.get("codigo_proveedor"),
                        "nombre_proveedor": prov.get("nombre_proveedor"),
                        "codigo_cliente": cli.get("codigo_cliente"),
                        "nombre_cliente": cli.get("nombre_cliente"),
                        "cantidades_vendidas": cli.get("cantidades_vendidas"),
                        "facturacion": cli.get("facturacion"),
                    }
                )
    return rows


def _nodo_ajustes_ventas_por_articulo(filas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Árbol sintético artículo → FA/NC de cabecera → clientes."""
    clientes: List[Dict[str, Any]] = []
    fact = 0.0
    for row in filas or []:
        f = float(row.get("facturacion") or 0)
        fact += f
        codigo = int(row.get("codigo_cliente") or 0)
        clientes.append(
            {
                "tipo": "cliente",
                "codigo_cliente": codigo,
                "nombre_cliente": (row.get("nombre_cliente") or "").strip() or f"Cliente {codigo}",
                "cantidades_vendidas": 0.0,
                "facturacion": f,
                "es_ajuste_cabecera": True,
            }
        )
    clientes.sort(
        key=lambda c: (
            (c.get("nombre_cliente") or "").upper(),
            int(c.get("codigo_cliente") or 0),
        )
    )
    return {
        "tipo": "articulo",
        "id_art": CODIGO_SINTETICO_AJUSTES,
        "nombre_articulo": NOMBRE_AJUSTES,
        "cantidades_vendidas": 0.0,
        "facturacion": fact,
        "es_ajuste_cabecera": True,
        "children": [
            {
                "tipo": "proveedor",
                "codigo_proveedor": 0,
                "nombre_proveedor": NOMBRE_FA_NC_CABECERA,
                "cantidades_vendidas": 0.0,
                "facturacion": fact,
                "es_ajuste_cabecera": True,
                "children": clientes,
            }
        ],
    }


def _stats_jerarquia_articulo_para_log(arbol: List[Dict[str, Any]]) -> Dict[str, int]:
    n_art = len(arbol)
    n_prov = 0
    n_cli = 0
    for art in arbol:
        for prov in art.get("children") or []:
            n_prov += 1
            n_cli += len(prov.get("children") or [])
    return {
        "articulos": n_art,
        "proveedores": n_prov,
        "clientes": n_cli,
        "vendedores": 0,
        "bloques_estado": 0,
        "nodos_rubro": 0,
        "nodos_subrubro": 0,
        "nodos_articulo": n_art,
    }


def _stats_jerarquia_para_log(arbol: List[Dict[str, Any]]) -> Dict[str, int]:
    """Conteos para diagnóstico (logs); no altera el payload."""
    nv = len(arbol)
    n_estado = 0
    n_cli = 0
    n_rub = 0
    n_sub = 0
    n_art = 0
    for g in arbol:
        for est in g.get("children") or []:
            n_estado += 1
            for cli in est.get("children") or []:
                if cli.get("tipo") != "cliente":
                    continue
                n_cli += 1
                for rub in cli.get("venta_detalle") or []:
                    if not isinstance(rub, dict):
                        continue
                    n_rub += 1
                    for sub in rub.get("children") or []:
                        if not isinstance(sub, dict):
                            continue
                        n_sub += 1
                        for art in sub.get("children") or []:
                            if isinstance(art, dict):
                                n_art += 1
    return {
        "vendedores": nv,
        "bloques_estado": n_estado,
        "clientes": n_cli,
        "nodos_rubro": n_rub,
        "nodos_subrubro": n_sub,
        "nodos_articulo": n_art,
    }


def run_ventas_objetivos_vs_bo(report: ReportDefinition, payload: Dict, user) -> QueryResult:
    svc = QueryRunnerService(user)
    filters = payload.get("filters", {}) or {}
    report_slug = getattr(report, "slug", None)
    solo_ventas_articulo = report_slug == "ventas-por-articulo"
    solo_ventas_periodo = report_slug in ("ventas-por-vendedor", "ventas-por-articulo")
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

    alcance_ctx = ctx_desde_runner(user, str(base_empresa), filters)
    alcance_cv = alcance_objetivos_cod_viajante(str(base_empresa), alcance_ctx)

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
    rubros_incluidos = _parse_int_list(filters.get("rubros_incluidos", []))
    rubros_excluidos = _parse_int_list(filters.get("rubros_excluidos", []))
    subrubros_incluidos = _parse_int_list(filters.get("subrubros_incluidos", []))
    subrubros_excluidos = _parse_int_list(filters.get("subrubros_excluidos", []))
    marcas_incluidos = _parse_int_list(filters.get("marcas_incluidos", []))
    marcas_excluidos = _parse_int_list(filters.get("marcas_excluidos", []))
    rubros_excluidos = [x for x in rubros_excluidos if x not in set(rubros_incluidos)]
    subrubros_excluidos = [x for x in subrubros_excluidos if x not in set(subrubros_incluidos)]
    marcas_excluidos = [x for x in marcas_excluidos if x not in set(marcas_incluidos)]
    vo_filtra_rubro = bool(rubros_incluidos) or bool(subrubros_incluidos)
    if solo_ventas_periodo and not solo_ventas_articulo:
        vo_filtra_rubro = False
    _tiene_filtros_catalogo = bool(
        rubros_incluidos
        or rubros_excluidos
        or subrubros_incluidos
        or subrubros_excluidos
        or marcas_incluidos
        or marcas_excluidos
    )
    vo_filtra_catalogo_articulo = solo_ventas_articulo and _tiene_filtros_catalogo
    vo_filtra_catalogo_vendedor = (
        solo_ventas_periodo and not solo_ventas_articulo and _tiene_filtros_catalogo
    )
    rub_sub_sql_art, rub_sub_params_art = _vo_sql_filtros_rubro_subrubro(
        "art", rubros_incluidos, subrubros_incluidos
    )
    rub_sub_sql_a, rub_sub_params_a = _vo_sql_filtros_rubro_subrubro("a", rubros_incluidos, subrubros_incluidos)
    cat_sql_art, cat_params_art = _vo_sql_filtros_articulo(
        "art",
        rubros_incluidos=rubros_incluidos,
        rubros_excluidos=rubros_excluidos,
        subrubros_incluidos=subrubros_incluidos,
        subrubros_excluidos=subrubros_excluidos,
        marcas_incluidos=marcas_incluidos,
        marcas_excluidos=marcas_excluidos,
    )
    ordenar_por, orden_forma = _parse_sorting(filters)
    if solo_ventas_periodo and ordenar_por in ("objetivo_meta", "objetivo_falta"):
        ordenar_por = "facturacion_periodo"
    metric_key = _METRIC_ORDER_MAP.get(ordenar_por) or "objetivo"

    # Reconciliación defensiva backend: si llega en ambos, prevalece "incluir".
    clientes_excluidos = [c for c in clientes_excluidos if int(c) not in set(clientes_incluir)]
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

    alcance_sql_cl, alcance_params_cl = _sql_in_viajantes("cl", alcance_viaj_filtro)
    alcance_sql_cl_bo, alcance_params_cl_bo = _sql_in_viajantes("cl_bo", alcance_viaj_filtro)
    alcance_sql_cl_rem, alcance_params_cl_rem = _sql_in_viajantes("cl_rem", alcance_viaj_filtro)
    alcance_sql_cl_ped, alcance_params_cl_ped = _sql_in_viajantes("cl_ped", alcance_viaj_filtro)
    alcance_sql_cl_uni, alcance_params_cl_uni = _sql_in_viajantes("cl_uni", alcance_viaj_filtro)
    alcance_sql_cl_res, alcance_params_cl_res = _sql_in_viajantes("cl_res", alcance_viaj_filtro)

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
    if alcance_viaj_filtro:
        reservado_viaj_clause += " AND cl_res.CodViajante IN (" + ",".join(str(x) for x in alcance_viaj_filtro) + ")"
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
    obj_viaj_params: List[Any] = []
    if vendedores_excluidos:
        obj_viaj_extra = (
            " AND v.Codigo IN (SELECT cjx.Codigo FROM cliente cjx WHERE cjx.CodViajante NOT IN ("
            + ",".join(str(x) for x in vendedores_excluidos)
            + "))"
        )
    if alcance_viaj_filtro:
        pha = ",".join(["%s"] * len(alcance_viaj_filtro))
        obj_viaj_extra += f" AND v.CodViajante IN ({pha})"
        obj_viaj_params.extend(alcance_viaj_filtro)

    viaj_bo = ""
    viaj_bo_params: List[Any] = []
    if vendedores_excluidos:
        phvb = ",".join(["%s"] * len(vendedores_excluidos))
        viaj_bo = f" AND cl_bo.CodViajante NOT IN ({phvb})"
        viaj_bo_params.extend(vendedores_excluidos)
    if alcance_viaj_filtro:
        viaj_bo += alcance_sql_cl_bo
        viaj_bo_params.extend(alcance_params_cl_bo)

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
            where_fac_cli_s = " AND ".join(where_fac_cli) + alcance_sql_cl
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
            cursor.execute(sql_fac_cli, params_fac_cli + alcance_params_cl)
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
            where_hist_cli_s = " AND ".join(where_hist_cli) + alcance_sql_cl
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
            cursor.execute(sql_hist_cli, params_hist_cli + alcance_params_cl)
            ids_con_historico_ventas = {int(r[0]) for r in cursor.fetchall() if r and r[0] is not None}
            _mark_phase("query_historico")

            rem_map: Dict[int, float] = {}
            ped_arm_map: Dict[int, float] = {}
            rem_art_detail: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(dict)
            ped_art_detail: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(dict)
            if not solo_ventas_periodo:
                filt_art_rp = (
                    f" AND {sql_excluir_tipo_art_gasto('a')}"
                    if not vo_filtra_rubro
                    else (
                        " AND a.IDArt IS NOT NULL AND "
                        + sql_excluir_tipo_art_gasto("a")
                        + rub_sub_sql_a
                    )
                )
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
                    WHERE {" AND ".join(where_remitos)}{alcance_sql_cl_rem}
                    GROUP BY cp.Codigo
                """
                cursor.execute(sql_rem_cli, params_rem + alcance_params_cl_rem)
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
                    WHERE {" AND ".join(where_ped_arm)}{alcance_sql_cl_ped}
                    GROUP BY cp.Codigo
                """
                cursor.execute(sql_ped_arm, params_ped + alcance_params_cl_ped)
                for r in cursor.fetchall():
                    ped_arm_map[int(r[0])] = float(r[1] or 0)
                _mark_phase("query_pedidos_en_armado")

                # --- REM / PED en armado por artículo (líneas stockp.PrecioNetoxR; verify / total consolidado) ---
                where_rem_w = " AND ".join(where_remitos)
                where_ped_w = " AND ".join(where_ped_arm)
                sql_rem_lineas_art = f"""
                    SELECT
                        cp.Codigo AS cod_cliente,
                        sp.IDArt AS id_art,
                        COALESCE(MAX(a.CodigoRubro), 0) AS codigo_rubro,
                        COALESCE(MAX(ru.NombreRubro), '') AS nombre_rubro,
                        COALESCE(MAX(a.IDSubRubro), 0) AS id_subrubro,
                        COALESCE(MAX(sr.NombreSubRubro), '') AS nombre_subrubro,
                        COALESCE(MAX(a.NombreArticulo), '') AS nombre_articulo,
                        SUM(COALESCE(sp.PrecioNetoxR, 0)) AS remitos_lineas
                    FROM comp_ped cp
                    INNER JOIN cliente cl_rem ON cl_rem.Codigo = cp.Codigo
                    INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
                        AND (sp.anulado IS NULL OR sp.anulado = 'No')
                        AND (sp.Comprobante = 'REM' OR sp.Comprobante IS NULL OR sp.Comprobante = '')
                    LEFT JOIN articulo a ON a.IDArt = sp.IDArt
                    LEFT JOIN rubro ru ON ru.CodigoRubro = a.CodigoRubro
                    LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
                    WHERE {where_rem_w}{filt_art_rp}
                    GROUP BY cp.Codigo, sp.IDArt
                    HAVING sp.IDArt IS NOT NULL AND sp.IDArt > 0
                        AND ABS(SUM(COALESCE(sp.PrecioNetoxR, 0))) > 0.00001
                """
                sql_ped_lineas_art = f"""
                    SELECT
                        cp.Codigo AS cod_cliente,
                        sp.IDArt AS id_art,
                        COALESCE(MAX(a.CodigoRubro), 0) AS codigo_rubro,
                        COALESCE(MAX(ru.NombreRubro), '') AS nombre_rubro,
                        COALESCE(MAX(a.IDSubRubro), 0) AS id_subrubro,
                        COALESCE(MAX(sr.NombreSubRubro), '') AS nombre_subrubro,
                        COALESCE(MAX(a.NombreArticulo), '') AS nombre_articulo,
                        SUM(COALESCE(sp.PrecioNetoxR, 0)) AS pedidos_armado_lineas
                    FROM comp_ped cp
                    INNER JOIN cliente cl_ped ON cl_ped.Codigo = cp.Codigo
                    INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
                        AND (sp.anulado IS NULL OR sp.anulado = 'No')
                        AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL OR sp.Comprobante = '')
                    LEFT JOIN articulo a ON a.IDArt = sp.IDArt
                    LEFT JOIN rubro ru ON ru.CodigoRubro = a.CodigoRubro
                    LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
                    WHERE {where_ped_w}{filt_art_rp}
                    GROUP BY cp.Codigo, sp.IDArt
                    HAVING sp.IDArt IS NOT NULL AND sp.IDArt > 0
                        AND ABS(SUM(COALESCE(sp.PrecioNetoxR, 0))) > 0.00001
                """
                params_rem_lineas = list(params_rem)
                params_ped_lineas = list(params_ped)
                if vo_filtra_rubro:
                    params_rem_lineas.extend(rub_sub_params_a)
                    params_ped_lineas.extend(rub_sub_params_a)
                cursor.execute(sql_rem_lineas_art, params_rem_lineas)
                for r in cursor.fetchall():
                    cid = int(r[0])
                    ida = int(r[1] or 0)
                    if ida <= 0:
                        continue
                    rem_art_detail[cid][ida] = {
                        "remitos_lineas": float(r[7] or 0),
                        "codigo_rubro": int(r[2] or 0),
                        "nombre_rubro": (r[3] or "").strip(),
                        "id_subrubro": int(r[4] or 0),
                        "nombre_subrubro": (r[5] or "").strip(),
                        "nombre_articulo": (r[6] or "").strip(),
                    }
                cursor.execute(sql_ped_lineas_art, params_ped_lineas)
                for r in cursor.fetchall():
                    cid = int(r[0])
                    ida = int(r[1] or 0)
                    if ida <= 0:
                        continue
                    ped_art_detail[cid][ida] = {
                        "pedidos_armado_lineas": float(r[7] or 0),
                        "codigo_rubro": int(r[2] or 0),
                        "nombre_rubro": (r[3] or "").strip(),
                        "id_subrubro": int(r[4] or 0),
                        "nombre_subrubro": (r[5] or "").strip(),
                        "nombre_articulo": (r[6] or "").strip(),
                    }
                _mark_phase("query_rem_ped_lineas_art")

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
                sql_excluir_tipo_art_gasto("art"),
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
                LEFT JOIN articulo art ON art.IDArt = st.IDArt
                WHERE {" AND ".join(where_uni)}{alcance_sql_cl_uni}
                GROUP BY cc.Codigo
            """
            cursor.execute(sql_uni, params_uni + alcance_params_cl_uni)
            uni_map: Dict[int, float] = {}
            for r in cursor.fetchall():
                uni_map[int(r[0])] = float(r[1] or 0)
                _mark_phase("query_unidades")

            # --- Detalle venta por línea (mismo rango y filtros que unidades) ---
            where_uni_s = " AND ".join(where_uni) + alcance_sql_cl_uni
            filt_art_venta_det = ""
            params_venta_art: List[Any] = list(params_uni) + list(alcance_params_cl_uni)
            if vo_filtra_rubro:
                filt_art_venta_det = f" AND art.IDArt IS NOT NULL{rub_sub_sql_art}"
                params_venta_art.extend(rub_sub_params_art)
            elif vo_filtra_catalogo_vendedor:
                filt_art_venta_det = f" AND art.IDArt IS NOT NULL{cat_sql_art}"
                params_venta_art.extend(cat_params_art)
            detalle_flat_por_cliente: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
            detalle_filas_articulo: List[Dict[str, Any]] = []
            ajustes_cabecera_vpa: List[Dict[str, Any]] = []
            signo_imp_linea = sql_signo_imp_post_pie_expr()
            if solo_ventas_articulo:
                where_art = list(where_uni)
                params_art: List[Any] = list(params_uni)
                filt_art_catalogo = ""
                if vo_filtra_catalogo_articulo:
                    filt_art_catalogo = f" AND art.IDArt IS NOT NULL{cat_sql_art}"
                    params_art.extend(cat_params_art)
                if clientes_incluir:
                    phc = ",".join(["%s"] * len(clientes_incluir))
                    where_art.append(f"cc.Codigo IN ({phc})")
                    params_art.extend(clientes_incluir)
                if vendedores_incluir:
                    phv = ",".join(["%s"] * len(vendedores_incluir))
                    where_art.append(f"cl_uni.CodViajante IN ({phv})")
                    params_art.extend(vendedores_incluir)
                where_art_s = " AND ".join(where_art)
                sql_venta_art_prov_cli = f"""
                    SELECT
                        COALESCE(art.IDArt, 0) AS id_art,
                        COALESCE(MAX(art.NombreArticulo), '') AS nombre_articulo,
                        COALESCE(art.CodigoProveedor, 0) AS codigo_proveedor,
                        COALESCE(MAX(prov.Nombre), '') AS nombre_proveedor,
                        cc.Codigo AS codigo_cliente,
                        COALESCE(MAX(cl_uni.nombre_cliente), '') AS nombre_cliente,
                        SUM({signo_imp_linea}) AS factu_linea,
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
                    LEFT JOIN proveedor prov ON prov.Codigo = art.CodigoProveedor
                    WHERE {where_art_s}{filt_art_catalogo}
                    GROUP BY art.IDArt, art.CodigoProveedor, cc.Codigo
                    HAVING art.IDArt IS NOT NULL AND art.IDArt > 0
                        AND (ABS(factu_linea) > 0.00001 OR ABS(unidades_linea) > 0.00001)
                """
                cursor.execute(sql_venta_art_prov_cli, params_art)
                for r in cursor.fetchall():
                    cod_prov = int(r[2] or 0)
                    detalle_filas_articulo.append(
                        {
                            "id_art": int(r[0] or 0),
                            "nombre_articulo": (r[1] or "").strip(),
                            "codigo_proveedor": cod_prov,
                            "nombre_proveedor": _nombre_proveedor_display(cod_prov, (r[3] or "").strip()),
                            "codigo_cliente": int(r[4] or 0),
                            "nombre_cliente": (r[5] or "").strip(),
                            "facturacion": float(r[6] or 0),
                            "cantidades_vendidas": float(r[7] or 0),
                        }
                    )
                if not vo_filtra_catalogo_articulo:
                    where_cc_parts = [
                        "cc.Fecha >= %s",
                        "cc.Fecha <= %s",
                        "cc.Anulado = 'No'",
                        "cc.CodigoMovimiento <> 0",
                        f"cc.TipoComprobante IN {TIPOS_COMP_VENTA}",
                    ]
                    params_cc: List[Any] = [fi_fac_sql, ff_fac_sql]
                    if sucursales_ints:
                        phs = ",".join(["%s"] * len(sucursales_ints))
                        where_cc_parts.append(f"cc.CodSucursal IN ({phs})")
                        params_cc.extend(sucursales_ints)
                    if puntos_venta_ints:
                        phpv = ",".join(["%s"] * len(puntos_venta_ints))
                        where_cc_parts.append(f"cc.id_pv IN ({phpv})")
                        params_cc.extend(puntos_venta_ints)
                    if clientes_excluidos:
                        ph = ",".join(["%s"] * len(clientes_excluidos))
                        where_cc_parts.append(f"cc.Codigo NOT IN ({ph})")
                        params_cc.extend(clientes_excluidos)
                    if clientes_incluir:
                        phc = ",".join(["%s"] * len(clientes_incluir))
                        where_cc_parts.append(f"cc.Codigo IN ({phc})")
                        params_cc.extend(clientes_incluir)
                    if vendedores_excluidos:
                        phv = ",".join(["%s"] * len(vendedores_excluidos))
                        where_cc_parts.append(f"cl.CodViajante NOT IN ({phv})")
                        params_cc.extend(vendedores_excluidos)
                    if vendedores_incluir:
                        phv = ",".join(["%s"] * len(vendedores_incluir))
                        where_cc_parts.append(f"cl.CodViajante IN ({phv})")
                        params_cc.extend(vendedores_incluir)
                    if alcance_viaj_filtro:
                        alcance_sql_cc, alcance_params_cc = _sql_in_viajantes("cl", alcance_viaj_filtro)
                        if alcance_sql_cc:
                            where_cc_parts.append(alcance_sql_cc.lstrip(" AND "))
                            params_cc.extend(alcance_params_cc)
                    ajustes_cabecera_vpa = consultar_ajustes_sin_mercaderia(
                        cursor,
                        where_cc_parts,
                        params_cc,
                        renglon_ok_sql=sql_excluir_tipo_art_gasto("art"),
                        group_by="cliente",
                    )
            else:
                sql_venta_por_art = f"""
                    SELECT
                        cc.Codigo AS id_cliente,
                        COALESCE(art.CodigoRubro, 0) AS codigo_rubro,
                        COALESCE(MAX(ru.NombreRubro), '') AS nombre_rubro,
                        COALESCE(art.IDSubRubro, 0) AS id_subrubro,
                        COALESCE(MAX(sr.NombreSubRubro), '') AS nombre_subrubro,
                        COALESCE(art.IDArt, 0) AS id_art,
                        COALESCE(MAX(art.NombreArticulo), '') AS nombre_articulo,
                        SUM({signo_imp_linea}) AS factu_linea,
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
                    WHERE {where_uni_s}{filt_art_venta_det}
                    GROUP BY cc.Codigo, art.CodigoRubro, art.IDSubRubro, art.IDArt
                    HAVING ABS(factu_linea) > 0.00001 OR ABS(unidades_linea) > 0.00001
                """
                cursor.execute(sql_venta_por_art, params_venta_art)
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
            if vo_filtra_catalogo_vendedor:
                fac_desde_det: Dict[int, float] = defaultdict(float)
                uni_desde_det: Dict[int, float] = defaultdict(float)
                for cid, lines in detalle_flat_por_cliente.items():
                    for linea in lines:
                        fac_desde_det[cid] += float(linea.get("facturacion") or 0)
                        uni_desde_det[cid] += float(linea.get("cantidades_vendidas") or 0)
                for cid in fact_map:
                    fact_map[cid]["facturacion"] = fac_desde_det.get(cid, 0.0)
                uni_map = {cid: uni_desde_det.get(cid, 0.0) for cid in set(uni_map) | set(fac_desde_det)}
            _mark_phase("query_detalle_ventas")

            objetivos_map: Dict[int, Decimal] = {}
            bo_cli_agg: Dict[int, Dict[str, float]] = defaultdict(
                lambda: {"bo_total": 0.0, "con_stock": 0.0, "con_ingreso": 0.0, "sin_stock": 0.0}
            )
            bo_art_detail: Dict[int, Dict[int, Dict[str, Any]]] = defaultdict(dict)
            if not solo_ventas_periodo:
                # --- Objetivos (solape con rango facturación) ---
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
                    cursor.execute(sql_obj, [ff, fi, ff, fi] + obj_viaj_params)
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
                    AND sp.Fecha >= %s AND sp.Fecha <= %s{clientes_excl_bo}{filt_art_rp}
                GROUP BY cp.Codigo, sp.IDArt, sd.stock_total, oc_pendiente_sub.oc_pendiente, reservado_sub.reservado
                HAVING bo_qty > 0
            """
                _bo_params: List[Any] = []
                if sucursales_ints:
                    _bo_params.extend(sucursales_ints)
                if puntos_venta_ints:
                    _bo_params.extend(puntos_venta_ints)
                _bo_params.extend(viaj_bo_params)
                _bo_params.extend([fecha_inicio_bo, fecha_fin_bo])
                if vo_filtra_rubro:
                    _bo_params.extend(rub_sub_params_a)
                cursor.execute(sql_bo_by_client, _bo_params)
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

            arbol: List[Dict[str, Any]] = []
            rows_out: List[Dict[str, Any]] = []

            if solo_ventas_articulo:
                arbol = _sort_arbol_ventas_por_articulo(
                    _nest_articulo_proveedor_cliente(detalle_filas_articulo),
                    metric_key,
                    orden_forma,
                )
                if ajustes_cabecera_vpa:
                    arbol.append(_nodo_ajustes_ventas_por_articulo(ajustes_cabecera_vpa))
                    arbol = pin_ajustes_al_final(
                        arbol,
                        es_ajuste=lambda n: int(n.get("id_art") or 0) == CODIGO_SINTETICO_AJUSTES,
                    )
                rows_out = _flatten_filas_ventas_por_articulo(arbol)
                _mark_phase("armado_jerarquia")
                _jstats = _stats_jerarquia_articulo_para_log(arbol)
                _total_ms = int((time.perf_counter() - started_at) * 1000)
                logger.info(
                    "[ventas_objetivos_bo] informe listo slug=%s filas_planas=%d articulos=%d "
                    "proveedores=%d clientes=%d tiempo_total_ms=%d fases_ms=%s",
                    report_slug,
                    len(rows_out),
                    _jstats["articulos"],
                    _jstats["proveedores"],
                    _jstats["clientes"],
                    _total_ms,
                    phase_ms,
                )
                tot = {
                    "facturacion": sum(float(x.get("facturacion") or 0) for x in rows_out),
                    "cantidades_vendidas": sum(float(x.get("cantidades_vendidas") or 0) for x in rows_out),
                    "total_articulos": len(arbol),
                    "total_clientes": len(rows_out),
                }
            else:
                all_ids = sorted(
                set(fact_map.keys())
                | ids_con_historico_ventas
                | set(rem_map.keys())
                | set(ped_arm_map.keys())
                | set(uni_map.keys())
                | set(bo_cli_agg.keys())
                | set(objetivos_map.keys())
                | set(rem_art_detail.keys())
                | set(ped_art_detail.keys())
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
                    fac_cli = float(row.get("facturacion") or 0)
                    uni_cli = float(row.get("cantidades_vendidas") or 0)
                    vd_tree = _nest_venta_detalle_rubro_subrubro_articulo(detalle_flat_por_cliente.get(cid, []))
                    if not solo_ventas_periodo:
                        _merge_bo_en_detalle_arbol(vd_tree, bo_art_detail.get(cid, {}))
                        _merge_rem_ped_lineas_en_detalle_arbol(
                            vd_tree,
                            rem_art_detail.get(cid, {}),
                            ped_art_detail.get(cid, {}),
                        )
                        _rollup_bo_en_detalle(vd_tree)
                        _rollup_rem_ped_lineas_en_detalle(vd_tree)
                    _rollup_facturacion_unidades_detalle(vd_tree)
                    if not solo_ventas_periodo and not vo_filtra_rubro:
                        _sf, _su = _sum_facturacion_unidades_hojas_detalle(vd_tree)
                        _append_articulo_residual_facturacion(vd_tree, fac_cli - _sf, uni_cli - _su)
                        _rollup_facturacion_unidades_detalle(vd_tree)
                    vd = _sort_nested_detalle(vd_tree, metric_key=metric_key, direction=orden_forma)
                    total_cli = float(row.get("total") or 0)
                    if solo_ventas_periodo:
                        estado_compra = "con_compra" if (abs(fac_cli) > 0.000001 or abs(uni_cli) > 0.000001) else "sin_compra"
                    else:
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

                arbol = agrupar_jerarquia_informe_arbol_org(str(base_empresa), alcance_ctx, arbol)

                rows_ordered: List[Dict[str, Any]] = []

                def _flatten_arbol_informe(nodos: List[Dict[str, Any]]) -> None:
                    for n in nodos or []:
                        if not isinstance(n, dict):
                            continue
                        if (n.get("tipo") or "vendedor") == "vendedor":
                            for estado in n.get("children") or []:
                                for ch in estado.get("children") or []:
                                    rows_ordered.append(
                                        {k: v for k, v in ch.items() if k not in ("tipo", "venta_detalle")}
                                    )
                        else:
                            _flatten_arbol_informe(n.get("children") or [])

                _flatten_arbol_informe(arbol)
                rows_out = rows_ordered
                _mark_phase("armado_jerarquia")

                _jstats = _stats_jerarquia_para_log(arbol)
                _total_ms = int((time.perf_counter() - started_at) * 1000)
                logger.info(
                    "[ventas_objetivos_bo] informe listo slug=%s clientes_grilla=%d vendedores=%d "
                    "estados_jerarquia=%d nodos_detalle rubro=%d subrubro=%d articulo=%d "
                    "tiempo_total_ms=%d fases_ms=%s",
                    report_slug,
                    len(rows_out),
                    _jstats["vendedores"],
                    _jstats["bloques_estado"],
                    _jstats["nodos_rubro"],
                    _jstats["nodos_subrubro"],
                    _jstats["nodos_articulo"],
                    _total_ms,
                    phase_ms,
                )

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
                "rubros_incluidos": rubros_incluidos,
                "rubros_excluidos": rubros_excluidos,
                "subrubros_incluidos": subrubros_incluidos,
                "subrubros_excluidos": subrubros_excluidos,
                "marcas_incluidos": marcas_incluidos,
                "marcas_excluidos": marcas_excluidos,
                "lista_precio": lista_precio,
                "lista_precio_label": _label_lista_precio(lista_precio),
                "ordenar_por": ordenar_por,
                "orden_forma": orden_forma,
            }
            filters_applied["performance_phase_ms"] = phase_ms
            filters_applied["performance_total_ms"] = int((time.perf_counter() - started_at) * 1000)
            if solo_ventas_periodo:
                notes.insert(0, f"Ventas del período (facturación y unidades): {fi_fac_sql} a {ff_fac_sql}.")
                if solo_ventas_articulo:
                    notes.append(
                        "Informe ventas por artículo: jerarquía artículo → proveedor → cliente; "
                        "sin objetivos, remitos, pedidos en armado ni backorder."
                    )
                    if vo_filtra_catalogo_articulo:
                        notes.append(
                            "Filtros rubro/subrubro/marca (incluir/excluir): limitan artículos "
                            "con ventas en el período de facturación."
                        )
                        notes.append(NOTA_AJUSTES_OMITIDOS_CATALOGO)
                    elif any(int(a.get("id_art") or 0) == CODIGO_SINTETICO_AJUSTES for a in arbol):
                        notes.append(NOTA_AJUSTES_INCLUIDOS)
                else:
                    notes.append(
                        "Informe ventas por vendedor: sin objetivos, remitos, pedidos en armado ni backorder; "
                        "jerarquía con/sin compra según facturación o unidades en el período."
                    )
                    if vo_filtra_catalogo_vendedor:
                        notes.append(
                            "Filtros rubro/subrubro/marca (incluir/excluir): limitan artículos "
                            "con ventas en el período de facturación; facturación y unidades del período "
                            "se calculan desde el detalle filtrado."
                        )
                if puntos_venta_ints:
                    notes.append(
                        f"Puntos de venta filtrados ({len(puntos_venta_ints)}): facturación y unidades/detalle usan cc.id_pv."
                    )
                notes.append(
                    f"Clientes en grilla: {len(rows_out)} "
                    "(histórico de ventas en cuentacliente sin acotar por ventana, más movimiento en el período seleccionado)."
                )
            else:
                notes.insert(
                    0,
                    f"Facturación/remitos: {fi_fac_sql} a {ff_fac_sql}. Backorder: {fecha_inicio_bo} a {fecha_fin_bo}.",
                )
                notes.append(
                    "Pedidos en armado: importe de PED en estado En preparación/Preparado, sin filtro por fechas "
                    "(misma semántica que el KPI del reporte total-consolidado-operativo)."
                )
                notes.append(
                    "Detalle por artículo: columnas remitos_lineas y pedidos_armado_lineas suman stockp.PrecioNetoxR "
                    "(REM solo en ventana de facturación; PED en armado sin filtro de fechas; líneas excluyen tipo_art Gasto)."
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
                if vo_filtra_rubro:
                    notes.append(
                        "Rubro/subrubro a incluir: el árbol de detalle y el BO por ítem solo muestran artículos que cumplen el filtro; "
                        "las columnas agregadas por cliente (facturación, unidades, remitos, pedidos, objetivos, total, falta) "
                        "siguen calculadas sin limitar por rubro/subrubro."
                    )
                notes.append(
                    "Si la suma del detalle por artículo (facturación y unidades del período) no iguala la cabecera del cliente, "
                    "se muestra la fila «Facturación sin desglose por artículo» (solo sin filtro rubro/subrubro activo)."
                )

            extra = {
                "tabs": {
                    "objetivos_jerarquia": arbol,
                    "objetivos_filas": rows_out,
                },
                "jerarquia_stats": _jstats,
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
