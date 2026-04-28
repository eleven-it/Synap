# -*- coding: utf-8 -*-
"""
Contratos puros para objetivos de venta vs informe (sin MySQL).

Ver docs/reports/SPEC_INFORME_OBJETIVOS_VENTAS_BO.md.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Union

Number = Union[Decimal, float, int, str, None]


def periodos_solapan(
    fecha_desde_a: date,
    fecha_hasta_a: date,
    fecha_desde_b: date,
    fecha_hasta_b: date,
) -> bool:
    """
    True si los intervalos cerrados [desde, hasta] se intersectan (inclusive en ambos extremos).
    """
    return fecha_desde_a <= fecha_hasta_b and fecha_desde_b <= fecha_hasta_a


def _to_decimal(value: Number) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def calcular_total_facturacion_remitos(facturacion: Number, remitos: Number) -> Decimal:
    """Total columna tipo Excel: Facturación + Remitos."""
    return _to_decimal(facturacion) + _to_decimal(remitos)


def calcular_falta(objetivo: Number, facturacion: Number, remitos: Number) -> Decimal:
    """
    Falta = Objetivo − Facturación − Remitos (regla acordada).
    Sin objetivo en datos se pasa 0 desde la capa que arma el informe.
    """
    return _to_decimal(objetivo) - _to_decimal(facturacion) - _to_decimal(remitos)


def objetivo_para_informe(
    objetivo_db: Number,
    fecha_desde_obj: date,
    fecha_hasta_obj: date,
    fecha_inicio_facturacion: date,
    fecha_fin_facturacion: date,
) -> Decimal:
    """
    Importe objetivo aplicable al informe si el intervalo del registro solapa
    el rango de facturación del filtro; si no solapa, 0.

    Si hay varios registros solapados para un mismo cliente, la capa SQL/ORM
    debe consolidar a uno (la validación de solapes en CRUD evita duplicados).
    """
    if not periodos_solapan(
        fecha_desde_obj,
        fecha_hasta_obj,
        fecha_inicio_facturacion,
        fecha_fin_facturacion,
    ):
        return Decimal("0")
    return _to_decimal(objetivo_db)
