"""Payloads de gráficos para reportes MPR (Chart.js en plantillas)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

MAX_RANKED_BARS = 12
MAX_CADENA_GAP = 8

_ESTADO_COLORS = {
    "completo": "#059669",
    "falta_parte": "#d97706",
    "falta_clasificar": "#7c3aed",
    "sin_envio": "#94a3b8",
}
_ESTADO_LABELS = {
    "completo": "Completo",
    "falta_parte": "Falta parte",
    "falta_clasificar": "Falta clasificar",
    "sin_envio": "Sin envío",
}


def _trunc_label(text: str, max_len: int = 36) -> str:
    s = (text or "").strip()
    if len(s) <= max_len:
        return s or "-"
    return s[: max_len - 1] + "…"


def build_charts_produccion(
    reporte: str,
    reporte_ctx: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Devuelve payload JSON-serializable para Chart.js o None si no aplica."""
    if reporte == "resumen_diario":
        return _chart_resumen_diario(reporte_ctx.get("dias") or [])
    if reporte == "operario":
        return _chart_operario(reporte_ctx.get("filas") or [])
    if reporte == "cadena":
        return _chart_cadena(reporte_ctx.get("filas") or [], reporte_ctx.get("kpis") or {})
    if reporte == "pendiente":
        return _chart_pendiente(reporte_ctx.get("filas") or [])
    return None


def _chart_resumen_diario(dias: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    con_datos = [d for d in (dias or []) if int(d.get("parte") or 0) > 0]
    if not con_datos:
        return None
    return {
        "reporte": "resumen_diario",
        "blocks": [
            {
                "id": "resumen-produccion",
                "kind": "line",
                "title": "Producción registrada por día",
                "subtitle": "Cantidad consolidada de partes registrados por día (pares)",
                "serie_label": "Producción",
                "color": "#059669",
                "labels": [str(d.get("fecha_display") or "") for d in con_datos],
                "values": [int(d.get("parte") or 0) for d in con_datos],
            }
        ],
    }


def _chart_operario(filas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not filas:
        return None
    top = filas[:MAX_RANKED_BARS]
    total = len(filas)
    blocks: List[Dict[str, Any]] = [
        {
            "id": "operario-hbar",
            "kind": "hbar",
            "title": "Ranking por pares producidos",
            "subtitle": (
                f"Top {len(top)} operarios"
                + (f" de {total}" if total > len(top) else "")
                + " · barras horizontales para comparar productividad"
            ),
            "labels": [_trunc_label(f.get("operario") or "-") for f in top],
            "values": [int(f.get("unidades") or 0) for f in top],
            "color": "#7c3aed",
        }
    ]
    tiene_calidad = any(
        int(f.get("semi") or 0) + int(f.get("segunda") or 0) + int(f.get("scrap") or 0) > 0
        for f in top
    )
    if tiene_calidad:
        blocks.append({
            "id": "operario-calidad-stacked",
            "kind": "hbar_stacked",
            "title": "Calidad por operario fabricante",
            "subtitle": "Apilado: semi elaborado · 2da selección · desperdicio (mismo top del ranking)",
            "labels": [_trunc_label(f.get("operario") or "-") for f in top],
            "datasets": [
                {
                    "label": "Semi elaborado",
                    "values": [int(f.get("semi") or 0) for f in top],
                    "color": "#059669",
                },
                {
                    "label": "2da selección",
                    "values": [int(f.get("segunda") or 0) for f in top],
                    "color": "#0ea5e9",
                },
                {
                    "label": "Scrap",
                    "values": [int(f.get("scrap") or 0) for f in top],
                    "color": "#d97706",
                },
            ],
        })
    return {
        "reporte": "operario",
        "blocks": blocks,
    }


def _chart_cadena(
    filas: List[Dict[str, Any]],
    kpis: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not filas:
        return None
    blocks: List[Dict[str, Any]] = [
        {
            "id": "cadena-funnel",
            "kind": "grouped_bar",
            "title": "Totales de planta en el período",
            "subtitle": "Embudo agregado: en fabricación → producido → semi elaborado → 2da selección (no es serie temporal)",
            "labels": ["En fabricación", "Producido", "Semi elaborado", "2da selección"],
            "datasets": [
                {
                    "label": "Pares",
                    "values": [
                        int(kpis.get("enviado") or 0),
                        int(kpis.get("parte") or 0),
                        int(kpis.get("semi") or 0),
                        int(kpis.get("segunda") or 0),
                    ],
                    "colors": ["#64748b", "#059669", "#0ea5e9", "#d97706"],
                }
            ],
        },
    ]

    estado_counts: Dict[str, int] = {}
    for f in filas:
        key = str(f.get("estado") or "sin_envio")
        estado_counts[key] = estado_counts.get(key, 0) + 1
    if estado_counts:
        labels_est = []
        values_est = []
        colors_est = []
        orden = ("falta_parte", "falta_clasificar", "sin_envio", "completo")
        for key in orden:
            if key in estado_counts:
                labels_est.append(_ESTADO_LABELS.get(key, key))
                values_est.append(estado_counts[key])
                colors_est.append(_ESTADO_COLORS.get(key, "#94a3b8"))
        blocks.append({
            "id": "cadena-estados",
            "kind": "doughnut",
            "title": "Componentes por estado de pipeline",
            "subtitle": "Cuántos SKUs están en cada etapa del flujo",
            "labels": labels_est,
            "values": values_est,
            "colors": colors_est,
        })

    top_gap = sorted(
        filas,
        key=lambda x: (-int(x.get("gap_envio_parte") or 0), str(x.get("codigo_manual") or x.get("codigo_articulo") or "")),
    )[:MAX_CADENA_GAP]
    top_gap = [f for f in top_gap if int(f.get("gap_envio_parte") or 0) > 0]
    if top_gap:
        blocks.append({
            "id": "cadena-gap-hbar",
            "kind": "hbar_grouped",
            "title": "Mayor brecha en fabricación → producido",
            "subtitle": f"Top {len(top_gap)} componentes con gap (detalle en tabla)",
            "labels": [_trunc_label(f.get("codigo_manual") or f.get("codigo_articulo") or "-", 20) for f in top_gap],
            "datasets": [
                {
                    "label": "En fabricación",
                    "values": [int(f.get("enviado") or 0) for f in top_gap],
                    "color": "#64748b",
                },
                {
                    "label": "Producido",
                    "values": [int(f.get("parte") or 0) for f in top_gap],
                    "color": "#059669",
                },
            ],
        })

    return {"reporte": "cadena", "blocks": blocks}


def _chart_pendiente(filas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not filas:
        return None
    top = sorted(
        filas,
        key=lambda x: (-float(x.get("pendiente") or 0), str(x.get("codigo_manual") or "")),
    )[:MAX_RANKED_BARS]
    return {
        "reporte": "pendiente",
        "blocks": [
            {
                "id": "pendiente-hbar",
                "kind": "hbar_colored",
                "title": "Mayor pendiente por componente",
                "subtitle": (
                    f"Top {len(top)} por pares pendientes"
                    + " · rojo = crítico (≥50 p.)"
                ),
                "labels": [_trunc_label(f.get("codigo_manual") or "-", 20) for f in top],
                "values": [int(float(f.get("pendiente") or 0)) for f in top],
                "colors": [
                    "#dc2626" if f.get("critico") else "#d97706"
                    for f in top
                ],
            }
        ],
    }
