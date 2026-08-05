"""
Preset SuperArt «Hombre» del informe ventas-marcas-mensual.

Persistido en ReportDefinition.config.preset_hombre (fila global, empresa=NULL).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from reports.models import ReportDefinition
from reports.services.ventas_marcas_mensual_seed import (
    VENTAS_MARCAS_MENSUAL_SLUG,
    ensure_ventas_marcas_mensual_report,
)

DEFAULT_PRESET_LABEL = "Hombre"
MAX_IDS = 500
MAX_ID_LEN = 64


def _get_report() -> Optional[ReportDefinition]:
    report = (
        ReportDefinition.objects.filter(
            slug=VENTAS_MARCAS_MENSUAL_SLUG,
            empresa__isnull=True,
            is_active=True,
        )
        .order_by("id")
        .first()
    )
    if report:
        return report
    return ensure_ventas_marcas_mensual_report()


def normalize_id_manuales(raw: Any) -> List[str]:
    """Normaliza lista de id_manual: strings no vacíos, únicos, orden estable."""
    if raw is None:
        return []
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        raise ValueError("«id_manuales» debe ser una lista de textos.")

    out: List[str] = []
    seen = set()
    for item in items:
        if item is None:
            continue
        s = str(item).strip()
        if not s:
            continue
        if len(s) > MAX_ID_LEN:
            raise ValueError(
                f"SuperArt «{s[:20]}…» supera {MAX_ID_LEN} caracteres."
            )
        key = s.casefold()
        if key in seen:
            continue
        if len(out) >= MAX_IDS:
            raise ValueError(f"Como máximo se admiten {MAX_IDS} SuperArts en el preset.")
        seen.add(key)
        out.append(s)
    return out


def read_preset_hombre(report: Optional[ReportDefinition] = None) -> Dict[str, Any]:
    """Lee preset desde config; defaults seguros si falta."""
    if report is None:
        report = _get_report()
    config = report.config if report and isinstance(report.config, dict) else {}
    preset = config.get("preset_hombre") if isinstance(config.get("preset_hombre"), dict) else {}
    ids = normalize_id_manuales(preset.get("id_manuales") or preset.get("ids") or [])
    label = str(preset.get("label") or DEFAULT_PRESET_LABEL).strip() or DEFAULT_PRESET_LABEL
    return {
        "label": label,
        "id_manuales": ids,
        "updated_by": str(preset.get("updated_by") or "").strip() or None,
    }


def set_preset_hombre(
    id_manuales: Any,
    *,
    user=None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persiste id_manuales del preset Hombre (merge parcial en config).
    Devuelve el preset almacenado.
    """
    ids = normalize_id_manuales(id_manuales)
    report = _get_report()
    if not report:
        raise ValueError("No se encontró la definición del informe ventas-marcas-mensual.")

    config = deepcopy(report.config) if isinstance(report.config, dict) else {}
    preset = (
        deepcopy(config["preset_hombre"])
        if isinstance(config.get("preset_hombre"), dict)
        else {}
    )
    preset["id_manuales"] = ids
    if label is not None:
        lbl = str(label).strip()
        if lbl:
            preset["label"] = lbl
    else:
        preset.setdefault("label", DEFAULT_PRESET_LABEL)

    if user is not None:
        cod = getattr(user, "cod_usuario", None) or getattr(user, "username", None)
        if cod:
            preset["updated_by"] = str(cod)

    config["preset_hombre"] = preset
    report.config = config
    report.save(update_fields=["config", "updated_at"])
    return read_preset_hombre(report)


def preset_hombre_payload(*, can_edit: bool) -> Dict[str, Any]:
    """Payload GET/PATCH para la UI."""
    preset = read_preset_hombre()
    return {
        "preset_hombre": preset,
        "can_edit": bool(can_edit),
    }
