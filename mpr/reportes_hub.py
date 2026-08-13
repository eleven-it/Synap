"""Hub de reportes MPR: routing, periodo y columnas CSV."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import to_date_or_none

GRUPOS_REPORTES: Dict[str, Dict[str, Any]] = {
    "produccion": {
        "label": "Producción",
        "reportes": {
            "resumen_diario": "Resumen diario",
            "operario": "Por operario",
            "operario_mensual": "Por operario (mensual)",
            "operario_maquina": "Por operario y máquina",
            "cadena": "Cadena pipeline",
            "pendiente": "Pendiente componentes",
        },
    },
    "demanda": {
        "label": "Demanda",
        "reportes": {
            "brecha_pack": "Brecha pack",
            "pedidos_estado": "Pedidos por estado",
            "stock": "Stock por depósito",
            "bajo_minimo": "Bajo mínimo",
        },
    },
    "trazabilidad": {
        "label": "Trazabilidad",
        "reportes": {
            "timeline": "Línea de tiempo",
            "movimientos": "Movimientos MPR",
            "conciliacion": "Conciliación envíos↔producción",
            "kardex_articulo": "Kardex artículo",
        },
    },
}

DEFAULT_GRUPO = "produccion"
DEFAULT_REPORTE = "resumen_diario"

# Redirección de bookmarks antiguos (?tipo=) — solo reportes MPR modernos (sin OPT).
TIPO_REDIRECT_MAP: Dict[str, Tuple[str, str]] = {
    "stock": ("demanda", "stock"),
    "bajo_minimo": ("demanda", "bajo_minimo"),
    "produccion_operario": ("produccion", "operario"),
}

UMBRAL_PENDIENTE_CRITICO = 50

PARTIALS: Dict[Tuple[str, str], str] = {
    ("produccion", "resumen_diario"): "mpr/reportes/partials/resumen_diario.html",
    ("produccion", "operario"): "mpr/reportes/partials/operario.html",
    ("produccion", "operario_mensual"): "mpr/reportes/partials/operario_mensual.html",
    ("produccion", "operario_maquina"): "mpr/reportes/partials/operario_maquina.html",
    ("produccion", "cadena"): "mpr/reportes/partials/cadena_pipeline.html",
    ("produccion", "pendiente"): "mpr/reportes/partials/pendiente_componentes.html",
    ("demanda", "brecha_pack"): "mpr/reportes/partials/brecha_pack.html",
    ("demanda", "pedidos_estado"): "mpr/reportes/partials/pedidos_estado.html",
    ("demanda", "stock"): "mpr/reportes/partials/stock.html",
    ("demanda", "bajo_minimo"): "mpr/reportes/partials/bajo_minimo.html",
    ("trazabilidad", "timeline"): "mpr/reportes/partials/trazabilidad_timeline.html",
    ("trazabilidad", "movimientos"): "mpr/reportes/partials/movimientos.html",
    ("trazabilidad", "conciliacion"): "mpr/reportes/partials/conciliacion.html",
    ("trazabilidad", "kardex_articulo"): "mpr/reportes/partials/kardex_articulo.html",
}

CSV_COLUMNAS: Dict[Tuple[str, str], List[Tuple[str, str]]] = {
    ("produccion", "resumen_diario"): [
        ("fecha_display", "Día"),
        ("parte", "Producción registrada"),
    ],
    ("produccion", "operario"): [
        ("operario", "Operario"),
        ("unidades", "Pares"),
        ("partes", "Partes"),
        ("componentes", "Componentes"),
        ("pct_total", "% del total"),
    ],
    ("produccion", "operario_mensual"): [
        ("operario", "Operario"),
        ("anio", "Año"),
        ("mes", "Mes"),
        ("valor", "Cantidad"),
    ],
    ("produccion", "operario_maquina"): [
        ("operario", "Operario"),
        ("maquina", "Máquina"),
        ("linea", "Línea"),
        ("declarada", "Declarada"),
        ("aprobada", "Aprobada"),
        ("gap", "Gap"),
        ("partes", "Partes"),
    ],
    ("trazabilidad", "conciliacion"): [
        ("codigo_articulo", "Código"),
        ("descripcion_articulo", "Componente"),
        ("enviado", "Enviado"),
        ("producido", "Producido"),
        ("no_respaldado", "No respaldado"),
    ],
    ("trazabilidad", "kardex_articulo"): [
        ("fecha_display", "Fecha"),
        ("tipo_mov", "Tipo"),
        ("nro_comprobante", "Comprobante"),
        ("detalle", "Detalle"),
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("saldo_corrido", "Saldo corrido"),
        ("operario", "Operario"),
    ],
    ("produccion", "cadena"): [
        ("codigo_articulo", "Código"),
        ("descripcion_articulo", "Componente"),
        ("enviado", "En fabricación"),
        ("parte", "Producido"),
        ("semi", "Semi elaborado"),
        ("segunda", "2da selección"),
        ("estado_label", "Estado"),
    ],
    ("produccion", "pendiente"): [
        ("codigo_manual", "Código"),
        ("descripcion_articulo", "Componente"),
        ("demanda", "Demanda"),
        ("total", "Stock pipeline"),
        ("pendiente", "Pendiente"),
        ("enviado", "Enviado"),
    ],
    ("demanda", "brecha_pack"): [
        ("codigo_articulo", "Código pack"),
        ("descripcion_articulo", "Pack"),
        ("demanda_pendiente", "Demanda"),
        ("stock_terminado", "Stock terminado"),
        ("cantidad_a_fabricar", "Brecha"),
        ("urgente_label", "Urgente"),
    ],
}


def _fmt_fecha_ui(d: Optional[date]) -> str:
    if not d:
        return ""
    return d.strftime("%d/%m/%Y")


def _to_date_obj_hub(value: Any) -> Optional[date]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = to_date_or_none(value)
    if not parsed:
        return None
    try:
        return datetime.strptime(str(parsed)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_periodo(
    fecha_desde_raw: Optional[str],
    fecha_hasta_raw: Optional[str],
) -> Dict[str, Any]:
    """Resuelve periodo con default últimos 7 días. Fechas internas ISO date."""
    hoy = date.today()
    default_desde = hoy - timedelta(days=6)
    fd = _to_date_obj_hub(fecha_desde_raw)
    fh = _to_date_obj_hub(fecha_hasta_raw)
    if fd is None:
        fd = default_desde
    if fh is None:
        fh = hoy
    if fd > fh:
        fd, fh = fh, fd
    return {
        "fecha_desde": fd,
        "fecha_hasta": fh,
        "fecha_desde_iso": fd.isoformat(),
        "fecha_hasta_iso": fh.isoformat(),
        "fecha_desde_display": _fmt_fecha_ui(fd),
        "fecha_hasta_display": _fmt_fecha_ui(fh),
    }


def resolver_grupo_reporte(get_params: Dict[str, str]) -> Tuple[str, str]:
    """
    Retorna (grupo, reporte).
    Bookmarks ?tipo=stock|bajo_minimo|produccion_operario redirigen al hub moderno.
    Tipos OPT legacy (pendiente, wip, desperdicio, opt_cerradas) caen al default.
    """
    tipo_antiguo = (get_params.get("tipo") or "").strip().lower()
    if tipo_antiguo and tipo_antiguo in TIPO_REDIRECT_MAP:
        return TIPO_REDIRECT_MAP[tipo_antiguo]

    grupo = (get_params.get("grupo") or DEFAULT_GRUPO).strip().lower()
    reporte = (get_params.get("reporte") or "").strip().lower()

    if grupo not in GRUPOS_REPORTES:
        grupo = DEFAULT_GRUPO
    reportes = GRUPOS_REPORTES[grupo]["reportes"]
    if not reporte or reporte not in reportes:
        reporte = DEFAULT_REPORTE if grupo == DEFAULT_GRUPO else next(iter(reportes))
    return grupo, reporte


def titulo_reporte(grupo: str, reporte: str) -> str:
    try:
        return GRUPOS_REPORTES[grupo]["reportes"][reporte]
    except KeyError:
        return "Reporte MPR"


def columnas_csv_para_modo(
    grupo: str,
    reporte: str,
    modo: str,
) -> List[Tuple[str, str]]:
    """Columnas CSV; en modo docenas usa claves *_display cuando existen."""
    from mpr.reportes_presentacion import CAMPOS_CANTIDAD

    base = CSV_COLUMNAS.get((grupo, reporte))
    if not base:
        return []
    if modo != "docenas":
        return list(base)
    out: List[Tuple[str, str]] = []
    for clave, titulo in base:
        if clave in CAMPOS_CANTIDAD:
            out.append((f"{clave}_display", titulo))
        else:
            out.append((clave, titulo))
    return out
