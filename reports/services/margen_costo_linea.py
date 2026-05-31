"""
Costo por renglón ``stock`` para margen ejecutivo.

Paridad AdministraNET informe de rentabilidad (vistas ``venta_rentabilidad_resumen`` /
``venta_rentabilidad_resumen_articulo`` y Crystal ``ventas_vista_rentabilidad_*.rpt``):
``SUM(PrecioCostoxR)`` con signo del comprobante; **sin** escala Display/Bulto ni
``Calculo_Costo_Display_Bulto`` (función sin call sites en facturación).
"""
from __future__ import annotations


def costo_linea_sin_signo_sql(*, stock_alias: str = "st") -> str:
    """Costo absoluto del renglón: ``PrecioCostoxR`` persistido en ``stock``."""
    st = stock_alias
    return f"COALESCE({st}.PrecioCostoxR, 0)"


def signed_costo_neto_linea_sql(
    *,
    stock_alias: str = "st",
    cc_alias: str = "cc",
) -> str:
    """``PrecioCostoxR`` con signo FA/NC (misma convención que venta neta del panel)."""
    linea = costo_linea_sin_signo_sql(stock_alias=stock_alias)
    cc = cc_alias
    return f"""CASE
        WHEN {cc}.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
            THEN {linea}
        WHEN {cc}.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
            THEN -({linea})
        ELSE 0
    END"""


def margen_costo_criterio_meta() -> str:
    return "precio_costoxr_linea"


def costo_linea_precio_costoxr_python(*, precio_costoxr: float) -> float:
    """Espejo Python de ``costo_linea_sin_signo_sql`` para tests unitarios."""
    return float(precio_costoxr or 0)
