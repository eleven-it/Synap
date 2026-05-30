"""
Normalización de costo por renglón ``stock`` para margen ejecutivo (Display/Bulto).

Paridad AdministraNET (``configuracion``): la escala por empaque aplica solo si
``utiliza_embalaje = 'Si'`` y (``utiliza_bulto_cerrado = 'Si'`` o ``utiliza_display = 'Si'``).
Si no, el costo es ``PrecioCostoxU × Cantidad`` (fallback ``PrecioCostoxR``).

Con embalaje activo, ``PrecioCostoxU`` es costo del **empaque comercial**; divisor:
- **Bulto:** ``multiplicador_comp``
- **Display/Unidad** con ``cantidad_dividir > 1``: ``cantidad_dividir``
- **Venta fraccionada TPV:** ``cantidad_unidad_display`` del renglón cuando ``cantidad_dividir = 1``
- **Excepción TPV:** ``Display`` + ambos divisores = 1 → ``PrecioCostoxR``
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _si(val: Any) -> bool:
    return str(val or "No").strip().lower() == "si"


def fetch_utiliza_embalaje_display_bulto(cursor) -> bool:
    """
    Indica si la empresa usa embalaje Display/Bulto (paridad VB6 ``Principal``).

    Requiere ``utiliza_embalaje = 'Si'`` y al menos uno de
    ``utiliza_bulto_cerrado`` / ``utiliza_display`` en ``'Si'``.
    """
    cols = ["utiliza_embalaje", "utiliza_bulto_cerrado", "utiliza_display"]
    try:
        cursor.execute(
            f"""
            SELECT COALESCE(utiliza_embalaje, 'No') AS utiliza_embalaje,
                   COALESCE(utiliza_bulto_cerrado, 'No') AS utiliza_bulto_cerrado,
                   COALESCE(utiliza_display, 'No') AS utiliza_display
            FROM configuracion
            LIMIT 1
            """
        )
    except Exception as exc:
        if "Unknown column" in str(exc):
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(utiliza_bulto_cerrado, 'No') AS utiliza_bulto_cerrado,
                           COALESCE(utiliza_display, 'No') AS utiliza_display
                    FROM configuracion
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if not row:
                    return False
                return _si(row[0]) or _si(row[1])
            except Exception as exc2:
                logger.warning("No se pudo leer config Display/Bulto: %s", exc2)
                return False
        logger.warning("No se pudo leer config embalaje Display/Bulto: %s", exc)
        return False

    row = cursor.fetchone()
    if not row:
        return False
    embalaje, bulto, display = row[0], row[1], row[2]
    return _si(embalaje) and (_si(bulto) or _si(display))


def _cantidad_dividir_sql(st: str = "st") -> str:
    return f"GREATEST(COALESCE({st}.cantidad_dividir, 1), 1)"


def _multiplicador_comp_sql(st: str = "st") -> str:
    return f"GREATEST(COALESCE({st}.multiplicador_comp, 1), 1)"


def _cantidad_unidad_display_sql(st: str = "st") -> str:
    return f"GREATEST(COALESCE({st}.cantidad_unidad_display, 1), 1)"


def _divisor_escala_sql(st: str = "st", tipo_expr: str | None = None) -> str:
    """Divisor para escalar costo de empaque a unidades vendidas en el renglón."""
    tipo = tipo_expr or f"COALESCE({st}.tipo_unidad, 'Unidad')"
    dividir = _cantidad_dividir_sql(st)
    mult = _multiplicador_comp_sql(st)
    display = _cantidad_unidad_display_sql(st)
    return f"""CASE
        WHEN {tipo} = 'Bulto' THEN {mult}
        WHEN {dividir} > 1 THEN {dividir}
        WHEN {display} > 1 THEN {display}
        ELSE 1
    END"""


def _costo_linea_simple_sql(st: str = "st") -> str:
    """Costo sin escala empaque (empresas sin Display/Bulto)."""
    u = f"COALESCE({st}.PrecioCostoxU, 0)"
    r = f"COALESCE({st}.PrecioCostoxR, 0)"
    cant = f"COALESCE({st}.Cantidad, 0)"
    return f"""CASE
        WHEN ABS({u}) > 0.000001 THEN ({u} * {cant})
        ELSE {r}
    END"""


def costo_linea_embalaje_sin_signo_sql(
    *,
    stock_alias: str = "st",
    articulo_alias: str = "a",
) -> str:
    """Costo con escala Display/Bulto (sin signo FA/NC)."""
    del articulo_alias
    st = stock_alias
    dividir = _cantidad_dividir_sql(st)
    display = _cantidad_unidad_display_sql(st)
    u = f"COALESCE({st}.PrecioCostoxU, 0)"
    r = f"COALESCE({st}.PrecioCostoxR, 0)"
    cant = f"COALESCE({st}.Cantidad, 0)"
    tipo = f"COALESCE({st}.tipo_unidad, 'Unidad')"
    divisor = _divisor_escala_sql(st, tipo)
    costo_escalado = f"(({u} * {cant}) / {divisor})"

    return f"""CASE
        WHEN {tipo} = 'Display' AND {dividir} <= 1 AND {display} <= 1 THEN {r}
        WHEN ABS({u}) > 0.000001 THEN {costo_escalado}
        ELSE {r}
    END"""


def costo_linea_sin_signo_sql(
    *,
    stock_alias: str = "st",
    articulo_alias: str = "a",
    utiliza_embalaje_display_bulto: bool = True,
) -> str:
    """Costo absoluto del renglón según configuración de embalaje de la empresa."""
    if not utiliza_embalaje_display_bulto:
        return _costo_linea_simple_sql(stock_alias)
    return costo_linea_embalaje_sin_signo_sql(
        stock_alias=stock_alias,
        articulo_alias=articulo_alias,
    )


def signed_costo_neto_linea_sql(
    *,
    stock_alias: str = "st",
    articulo_alias: str = "a",
    cc_alias: str = "cc",
    utiliza_embalaje_display_bulto: bool = True,
) -> str:
    """Costo normalizado con signo factura / nota de crédito."""
    linea = costo_linea_sin_signo_sql(
        stock_alias=stock_alias,
        articulo_alias=articulo_alias,
        utiliza_embalaje_display_bulto=utiliza_embalaje_display_bulto,
    )
    cc = cc_alias
    return f"""CASE
        WHEN {cc}.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
            THEN {linea}
        WHEN {cc}.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
            THEN -({linea})
        ELSE 0
    END"""


def margen_costo_criterio_meta(utiliza_embalaje_display_bulto: bool) -> str:
    if utiliza_embalaje_display_bulto:
        return "costo_empaque_escala_cantidad_dividir"
    return "costo_unitario_precio_costoxu_cantidad"


def _normalize_tipo_unidad(tipo_unidad: Optional[str]) -> str:
    t = (tipo_unidad or "Unidad").strip()
    return t if t else "Unidad"


def _safe_divisor(value: float, default: float = 1.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v <= 0:
        return default
    return v


def _divisor_escala_python(
    *,
    tipo_unidad: str,
    cantidad_dividir: float,
    cantidad_unidad_display: float,
    multiplicador_comp: float,
) -> float:
    if tipo_unidad == "Bulto":
        return multiplicador_comp
    if cantidad_dividir > 1:
        return cantidad_dividir
    if cantidad_unidad_display > 1:
        return cantidad_unidad_display
    return 1.0


def costo_linea_normalizado_python(
    *,
    precio_costoxu: float,
    precio_costoxr: float,
    cantidad: float,
    tipo_unidad: Optional[str] = None,
    precio_unidad: Optional[str] = None,
    cantidad_dividir: Optional[float] = None,
    cantidad_unidad_display: Optional[float] = None,
    multiplicador_comp: Optional[float] = None,
    utiliza_embalaje_display_bulto: bool = True,
) -> float:
    """Espejo Python de ``costo_linea_sin_signo_sql`` para tests unitarios."""
    del precio_unidad

    u = float(precio_costoxu or 0)
    r = float(precio_costoxr or 0)
    cant = float(cantidad or 0)

    if not utiliza_embalaje_display_bulto:
        if abs(u) > 1e-9:
            return u * cant
        return r

    dividir = _safe_divisor(cantidad_dividir, 1.0)
    display = _safe_divisor(cantidad_unidad_display, 1.0)
    mult = _safe_divisor(multiplicador_comp, 1.0)
    tipo = _normalize_tipo_unidad(tipo_unidad)

    if tipo == "Display" and dividir <= 1 and display <= 1:
        return r

    if abs(u) > 1e-9:
        divisor = _divisor_escala_python(
            tipo_unidad=tipo,
            cantidad_dividir=dividir,
            cantidad_unidad_display=display,
            multiplicador_comp=mult,
        )
        return (u * cant) / divisor
    return r
