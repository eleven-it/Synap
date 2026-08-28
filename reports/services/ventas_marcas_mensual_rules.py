# -*- coding: utf-8 -*-
"""
Reglas compartidas Ventas marcas mensual / licenciatarios híbrido.

Fuente única de verdad para tipos de comprobante, signos, anulados y factor U.M.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Tuple

from core.utils.administranet_types import str_or_default, to_decimal_or_none

from reports.services.articulo_venta_sql import sql_solo_tipo_art_articulo
from reports.services.comprobante_descuento_cabecera import sql_factor_descuento_cabecera_expr

TIPOS_FAC: Tuple[str, ...] = ("FA", "FB", "FC", "FE", "FM")
TIPOS_NC: Tuple[str, ...] = ("NCA", "NCB", "NCC", "NCE", "NCM")
STOCK_TIPO_COMP: Tuple[str, ...] = ("Venta", "Venta TPV", "Devol - Cliente", "ND Anul NC")

FACTOR_DOCENAS_MAP = {
    "P1": 12.0,
    "P2": 6.0,
    "P3": 4.0,
    "P6": 2.0,
    "CU": 1.0,
    "UNIDAD": 1.0,
    "UNI": 1.0,
    "UNIDADES": 1.0,
}


def factor_docenas_unimed(nombre_unimed: str | None) -> float:
    """Factor divisor docenas desde unidad de medida AdministraNET."""
    um = str_or_default(nombre_unimed, "").strip().upper()
    return FACTOR_DOCENAS_MAP.get(um, 1.0)


def sql_factor_docenas_expr() -> str:
    return """
        CASE COALESCE(st.nombre_unimed_vta, um.nombre_unimed, '')
            WHEN 'P1' THEN 12
            WHEN 'P2' THEN 6
            WHEN 'P3' THEN 4
            WHEN 'P6' THEN 2
            WHEN 'CU' THEN 1
            WHEN 'UNIDAD' THEN 1
            WHEN 'UNI' THEN 1
            WHEN 'UNIDADES' THEN 1
            ELSE 1
        END
    """


def sql_signo_qty_expr() -> str:
    fac = ",".join(f"'{t}'" for t in TIPOS_FAC)
    nc = ",".join(f"'{t}'" for t in TIPOS_NC)
    return f"""
        CASE
            WHEN cc.TipoComprobante IN ({fac}) THEN COALESCE(st.Cantidad, 0)
            WHEN cc.TipoComprobante IN ({nc}) THEN -COALESCE(st.Cantidad, 0)
            ELSE 0
        END
    """


def sql_signo_imp_expr() -> str:
    fac = ",".join(f"'{t}'" for t in TIPOS_FAC)
    nc = ",".join(f"'{t}'" for t in TIPOS_NC)
    return f"""
        CASE
            WHEN cc.TipoComprobante IN ({fac}) THEN COALESCE(st.PrecioNetoxR, 0)
            WHEN cc.TipoComprobante IN ({nc}) THEN -COALESCE(st.PrecioNetoxR, 0)
            ELSE 0
        END
    """


def sql_signo_imp_post_pie_expr() -> str:
    """Importe renglón post-pie: signo FAC/NC × PrecioNetoxR × factor cabecera."""
    fac = ",".join(f"'{t}'" for t in TIPOS_FAC)
    nc = ",".join(f"'{t}'" for t in TIPOS_NC)
    factor = sql_factor_descuento_cabecera_expr()
    return f"""
        CASE
            WHEN cc.TipoComprobante IN ({fac}) THEN
                COALESCE(st.PrecioNetoxR, 0) * ({factor})
            WHEN cc.TipoComprobante IN ({nc}) THEN
                -COALESCE(st.PrecioNetoxR, 0) * ({factor})
            ELSE 0
        END
    """


def sql_comprobantes_in_clause() -> str:
    all_types = TIPOS_FAC + TIPOS_NC
    return ",".join(f"'{t}'" for t in all_types)


def sql_stock_tipo_comp_in_clause() -> str:
    return ",".join(f"'{t}'" for t in STOCK_TIPO_COMP)


def sql_base_where_clauses(date_from_param: str = "%s", date_to_param: str = "%s") -> list[str]:
    """Cláusulas WHERE base VMM: fechas, anulados, tipos comprobante, stock y solo Articulo."""
    return [
        f"cc.Fecha >= {date_from_param}",
        f"cc.Fecha <= {date_to_param}",
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
        f"cc.TipoComprobante IN ({sql_comprobantes_in_clause()})",
        "st.Anulado = 'No'",
        f"st.TipoComp IN ({sql_stock_tipo_comp_in_clause()})",
        sql_solo_tipo_art_articulo("art"),
    ]


def apply_comprobante_sign(
    tipo_comprobante: str,
    cantidad,
    importe,
) -> Tuple[Decimal, Decimal]:
    """Aplica signo FAC (+) / NC (−) como en ventas_marcas_mensual_runner."""
    qty = to_decimal_or_none(cantidad) or Decimal("0")
    amt = to_decimal_or_none(importe) or Decimal("0")
    tipo = str_or_default(tipo_comprobante, "").strip().upper()
    if tipo in TIPOS_FAC:
        return qty, amt
    if tipo in TIPOS_NC:
        return -qty, -amt
    return Decimal("0"), Decimal("0")


def compute_units_amount_for_pack(
    *,
    cantidad,
    importe,
    nombre_unimed: str | None,
    unit_mode: str,
    tipo_comprobante: str = "FA",
) -> Tuple[Decimal, Decimal]:
    """
    Calcula unidades e importe para un pack licenciatario.

    DZ: cantidad / factor; PK/packs: cantidad cruda. Misma facturación en ambos modos LEV.
    """
    signed_qty, signed_amt = apply_comprobante_sign(tipo_comprobante, cantidad, importe)
    mode = str_or_default(unit_mode, "").strip().lower()
    if mode == "dozens":
        factor = Decimal(str(factor_docenas_unimed(nombre_unimed)))
        if factor == 0:
            factor = Decimal("1")
        units = signed_qty / factor
    else:
        units = signed_qty
    return units, signed_amt


def iter_allowed_comprobantes() -> Iterable[str]:
    yield from TIPOS_FAC
    yield from TIPOS_NC
