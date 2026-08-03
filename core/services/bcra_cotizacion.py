"""Cliente HTTP BCRA para sugerencia de cotización dólar."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.utils.administranet_types import to_decimal_or_none

logger = logging.getLogger(__name__)

BCRA_API_BASE = "https://api.bcra.gob.ar/estadisticas/v2.0/datosvariable"

# IDs configurables (validar contra API real en staging).
BCRA_VARIABLE_IDS: Dict[str, int] = {
    "bcra_referencia": 3500,
    "bcra_compra": 9790,
    "bcra_venta": 4,
}

_CACHE: Dict[str, Dict[str, Any]] = {}


def _cache_key(tipo: str, fecha: date) -> str:
    return f"{tipo}:{fecha.isoformat()}"


def _fetch_variable(id_variable: int, fecha: date, timeout_seg: int) -> Optional[Decimal]:
    desde = (fecha - timedelta(days=7)).isoformat()
    hasta = fecha.isoformat()
    url = f"{BCRA_API_BASE}/{id_variable}/{desde}/{hasta}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "Synap/1.0"})
    try:
        with urlopen(req, timeout=timeout_seg) as resp:
            import json

            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        logger.warning("BCRA API no disponible (var=%s): %s", id_variable, exc)
        return None

    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results:
        return None

    # Último valor con fecha <= corte (carry-forward dentro del rango).
    elegido = None
    for row in results:
        if not isinstance(row, dict):
            continue
        f_raw = row.get("fecha")
        val = to_decimal_or_none(row.get("valor"))
        if val is None or val <= 0 or not f_raw:
            continue
        try:
            f_row = date.fromisoformat(str(f_raw)[:10])
        except ValueError:
            continue
        if f_row <= fecha:
            if elegido is None or f_row >= elegido[0]:
                elegido = (f_row, val)
    return elegido[1] if elegido else None


def consultar_bcra(
    tipo_cotizacion: str,
    *,
    fecha: Optional[date] = None,
    timeout_seg: int = 5,
    usar_cache: bool = True,
) -> Dict[str, Any]:
    """
    Consulta BCRA según tipo configurado. Fail-soft: nunca lanza hacia la UI.

    Retorna dict con claves: valor, fecha, tipo, disponible, mensaje.
    """
    corte = fecha or date.today()
    if tipo_cotizacion == "manual_only":
        return {
            "valor": None,
            "fecha": corte.isoformat(),
            "tipo": tipo_cotizacion,
            "disponible": False,
            "mensaje": "La empresa está configurada en modo solo manual.",
        }

    ck = _cache_key(tipo_cotizacion, corte)
    if usar_cache and ck in _CACHE:
        return dict(_CACHE[ck])

    valor: Optional[Decimal] = None
    if tipo_cotizacion == "mid":
        compra = _fetch_variable(BCRA_VARIABLE_IDS["bcra_compra"], corte, timeout_seg)
        venta = _fetch_variable(BCRA_VARIABLE_IDS["bcra_venta"], corte, timeout_seg)
        if compra is not None and venta is not None:
            valor = (compra + venta) / Decimal("2")
        elif venta is not None:
            valor = venta
        elif compra is not None:
            valor = compra
    else:
        var_id = BCRA_VARIABLE_IDS.get(tipo_cotizacion)
        if var_id is None:
            return {
                "valor": None,
                "fecha": corte.isoformat(),
                "tipo": tipo_cotizacion,
                "disponible": False,
                "mensaje": f"Tipo de cotización «{tipo_cotizacion}» no mapeado a variable BCRA.",
            }
        valor = _fetch_variable(var_id, corte, timeout_seg)

    if valor is None:
        resultado = {
            "valor": None,
            "fecha": corte.isoformat(),
            "tipo": tipo_cotizacion,
            "disponible": False,
            "mensaje": "No se pudo obtener sugerencia BCRA.",
        }
    else:
        resultado = {
            "valor": float(valor),
            "fecha": corte.isoformat(),
            "tipo": tipo_cotizacion,
            "disponible": True,
            "mensaje": "",
        }

    if usar_cache:
        _CACHE[ck] = dict(resultado)
    return resultado


def limpiar_cache_bcra() -> None:
    """Útil en tests."""
    _CACHE.clear()
