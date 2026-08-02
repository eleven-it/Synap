"""
Visibilidad de áreas del Command Center (config global).

Persistencia: ReportDefinition.config del slug command-center-gerencial (empresa=null).
Schema:
  config.command_center.areas = { ventas: bool, inventario: bool, ... }
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from django.db.models import Q

from reports.models import ReportCategory, ReportDefinition
from reports.services.report_visibility import COMMAND_CENTER_SLUG

CC_AREA_KEYS = (
    "ventas",
    "inventario",
    "compras",
    "manufactura",
    "cruzados",
    "tesoreria",
    "ventas_cobros",
)

DEFAULT_CC_AREAS: Dict[str, bool] = {key: True for key in CC_AREA_KEYS}

CC_AREA_LABELS: Dict[str, str] = {
    "ventas": "Ventas",
    "inventario": "Inventario",
    "compras": "Compras",
    "manufactura": "Manufactura (MPR)",
    "cruzados": "Demanda pendiente",
    "tesoreria": "Tesorería",
    "ventas_cobros": "Ventas por cobro",
}

# Detalle UI / detail_urls → área padre
DETAIL_KEY_TO_AREA: Dict[str, str] = {
    "pedidos_pendientes": "ventas",
    "remitos_nf": "ventas",
    "ventas_marcas_mensual": "ventas",
    "existencias": "inventario",
    "backorder": "cruzados",
    "cobros_detalle": "ventas_cobros",
    "movimientos_caja": "tesoreria",
}

AREA_DISABLED_PAYLOAD = {
    "disponible": False,
    "motivo": "area_deshabilitada",
    "error": {
        "tipo": "area_deshabilitada",
        "mensaje": "Área deshabilitada en la configuración del Command Center.",
    },
}


def get_cc_report_definition() -> Optional[ReportDefinition]:
    """Definición global del Command Center (empresa nula)."""
    return ReportDefinition.objects.filter(
        Q(slug=COMMAND_CENTER_SLUG, is_active=True, empresa__isnull=True)
    ).first()


def ensure_cc_report_definition() -> ReportDefinition:
    """Obtiene o crea la fila global del CC con defaults de áreas."""
    report = get_cc_report_definition()
    if report:
        return report
    report = ReportDefinition.objects.create(
        empresa=None,
        slug=COMMAND_CENTER_SLUG,
        name="Command Center",
        description="Vista consolidada gerencial por área.",
        category=ReportCategory.MANAGERIAL,
        config={"command_center": {"areas": dict(DEFAULT_CC_AREAS)}},
        is_active=True,
        is_visible=True,
        show_in_catalog=True,
    )
    return report


def _normalize_areas(raw: Any) -> Dict[str, bool]:
    out = dict(DEFAULT_CC_AREAS)
    if not isinstance(raw, dict):
        return out
    for key in CC_AREA_KEYS:
        if key in raw:
            out[key] = bool(raw[key])
    return out


def read_cc_areas_config(report: Optional[ReportDefinition] = None) -> Dict[str, bool]:
    """Áreas persistidas (sin gate MPR)."""
    report = report if report is not None else get_cc_report_definition()
    if not report:
        return dict(DEFAULT_CC_AREAS)
    config = report.config if isinstance(report.config, dict) else {}
    cc = config.get("command_center") if isinstance(config.get("command_center"), dict) else {}
    return _normalize_areas(cc.get("areas"))


def resolve_cc_areas(*, mpr_active: bool, report: Optional[ReportDefinition] = None) -> Dict[str, bool]:
    """
    Áreas efectivas para UI/API.

    Manufactura requiere flag de config AND módulo MPR activo.
    """
    areas = read_cc_areas_config(report)
    if not mpr_active:
        areas["manufactura"] = False
    return areas


def is_cc_area_enabled(area_key: str, *, mpr_active: Optional[bool] = None) -> bool:
    """True si el área está habilitada efectivamente."""
    if area_key not in CC_AREA_KEYS:
        return False
    if mpr_active is None:
        from reports.services.executive_dashboard.base import mpr_modulo_activo

        mpr_active = mpr_modulo_activo()
    return bool(resolve_cc_areas(mpr_active=mpr_active).get(area_key))


def set_cc_areas(areas_patch: Dict[str, Any], user=None) -> Dict[str, bool]:
    """
    Persiste flags globales. Solo keys conocidas; merge sobre defaults/config actual.
    Devuelve el config almacenado (sin gate MPR).
    """
    if not isinstance(areas_patch, dict):
        raise ValueError("El cuerpo 'areas' debe ser un objeto.")
    unknown = set(areas_patch.keys()) - set(CC_AREA_KEYS)
    if unknown:
        raise ValueError(
            "Áreas desconocidas: " + ", ".join(sorted(unknown))
        )

    report = ensure_cc_report_definition()
    current = read_cc_areas_config(report)
    for key, value in areas_patch.items():
        current[key] = bool(value)

    config = deepcopy(report.config) if isinstance(report.config, dict) else {}
    cc = config.get("command_center") if isinstance(config.get("command_center"), dict) else {}
    cc["areas"] = current
    if user is not None:
        cod = getattr(user, "cod_usuario", None) or getattr(user, "username", None)
        if cod:
            cc["areas_updated_by"] = str(cod)
    config["command_center"] = cc
    report.config = config
    report.save(update_fields=["config", "updated_at"])
    return current


def filter_urls_by_areas(
    urls: Dict[str, str],
    areas: Dict[str, bool],
    *,
    key_to_area: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Filtra un dict de URLs dejando solo las de áreas habilitadas."""
    mapping = key_to_area or {k: k for k in urls}
    out: Dict[str, str] = {}
    for key, url in urls.items():
        area = mapping.get(key, key)
        if areas.get(area, False):
            out[key] = url
    return out


def areas_catalog(*, mpr_active: bool) -> Dict[str, Any]:
    """Payload GET para UI de configuración."""
    stored = read_cc_areas_config()
    effective = resolve_cc_areas(mpr_active=mpr_active)
    return {
        "areas_config": stored,
        "areas": effective,
        "labels": dict(CC_AREA_LABELS),
        "keys": list(CC_AREA_KEYS),
        "mpr_module_active": bool(mpr_active),
    }
