"""Resolución de CotizacionConfig por empresa (Postgres)."""
from __future__ import annotations

from typing import Any, Dict

from core.models.cotizacion_config import CotizacionConfig


def _defaults_globales() -> Dict[str, Any]:
    return {
        "base_empresa": CotizacionConfig.BASE_DEFAULT,
        "id_cotizacion": 1,
        "tipo_cotizacion": "bcra_referencia",
        "auto_aceptar_job": False,
        "timeout_seg": 5,
    }


def resolver_cotizacion_config(base_empresa: str) -> Dict[str, Any]:
    """Carga config global __default__ y aplica override por empresa."""
    efectiva = _defaults_globales()
    try:
        global_cfg = CotizacionConfig.objects.get(base_empresa=CotizacionConfig.BASE_DEFAULT)
        efectiva.update(
            {
                "id_cotizacion": global_cfg.id_cotizacion,
                "tipo_cotizacion": global_cfg.tipo_cotizacion,
                "auto_aceptar_job": global_cfg.auto_aceptar_job,
                "timeout_seg": global_cfg.timeout_seg,
            }
        )
    except CotizacionConfig.DoesNotExist:
        pass

    be = (base_empresa or "").strip()
    if be and be != CotizacionConfig.BASE_DEFAULT:
        try:
            emp_cfg = CotizacionConfig.objects.get(base_empresa=be)
            efectiva.update(
                {
                    "id_cotizacion": emp_cfg.id_cotizacion,
                    "tipo_cotizacion": emp_cfg.tipo_cotizacion,
                    "auto_aceptar_job": emp_cfg.auto_aceptar_job,
                    "timeout_seg": emp_cfg.timeout_seg,
                }
            )
        except CotizacionConfig.DoesNotExist:
            pass

    efectiva["base_empresa_resuelta"] = be or CotizacionConfig.BASE_DEFAULT
    return efectiva
