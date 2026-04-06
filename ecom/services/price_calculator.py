"""
Cálculo de precios alineado a SPEC_PRECIOS.md (paridad con util-calculaprecio.inc.php — subconjunto).
Solo Decimal; sin float en cálculos.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# Listas numéricas: 1..5 = Lista 1..5, 6 = Lista Oficial (SPEC B.1)
LISTAS_PRECIO_VALIDAS = frozenset({1, 2, 3, 4, 5, 6})

Q2 = Decimal("0.01")
Q4 = Decimal("0.0001")


class ListaPrecioInvalidaError(ValueError):
    """lista_id fuera de LISTAS_PRECIO_VALIDAS (PHP dejaba variables indefinidas)."""


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


def validar_lista_precio(lista_id: int) -> None:
    # [SPEC B.1] Mapeo de lista; fuera de rango → error explícito en Synap
    if lista_id not in LISTAS_PRECIO_VALIDAS:
        raise ListaPrecioInvalidaError(
            f"lista_id debe estar en {sorted(LISTAS_PRECIO_VALIDAS)}; recibido {lista_id!r}"
        )


def normalizar_descuento_porcentual(descuento: Decimal) -> Decimal:
    """[SPEC D] Descuento > 100% se trata como 100%. Negativos → 0."""
    if descuento < 0:
        return Decimal("0")
    if descuento > 100:
        return Decimal("100")
    return descuento


def vigencia_promo(
    desde: date | datetime | str | None,
    hasta: date | datetime | str | None,
) -> bool:
    """
    [SPEC B.9] Vigencia de promoción (paridad con PHP vigencia_promo, sin idArt/conn).
    Año de hasta > 2038 se ajusta a 2037 antes de evaluar (workaround PHP).
    """
    hoy = date.today()

    def _parse(d: date | datetime | str | None) -> date | None:
        if d is None:
            return None
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, date):
            return d
        parts = str(d).split("-")
        y = int(parts[0])
        if y > 2038:
            y = 2037
            parts[0] = str(y)
            d = "-".join(parts)
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()

    d0 = _parse(desde)
    d1 = _parse(hasta)

    if d0 is not None and d1 is not None:
        return d0 <= hoy <= d1
    if d0 is None and d1 is None:
        return True
    if d0 is None and d1 is not None:
        return hoy <= d1
    # Resta: d0 definido, hasta ausente
    return hoy >= d0


def calcular_precio(
    precio_base: Decimal,
    lista_id: int,
    descuento_cliente: Decimal,
    **kwargs: Any,
) -> Decimal:
    """
    [SPEC B.2–B.4] Precio neto o final según flags.

    - precio_base: neto de lista (equivalente a Precio{i}V ya resuelto por el caller).
    - lista_id: 1..5 o 6 Lista Oficial (validación; el precio base ya corresponde a esa lista).
    - descuento_cliente: porcentaje 0–100 sobre precio_base (descuento de renglón/cliente).

    kwargs opcionales:
    - incluir_iva: bool = False — si True, devuelve precio final con IVA (+ interno).
    - alicuota_iva: Decimal — por defecto 21.
    - impuesto_interno_pct: Decimal — % sobre neto tras descuento.
    - tipo_cliente: str | None — si es None, no aplica descuento cliente ([SPEC D] cliente sin tipo).
    - promo_tipo: str | None — si "Monto fijo", usa rama promo (precio final TTC en promo_porc).
    - promo_porc: Decimal — monto TTC para Monto fijo (SPEC B.5).
    - alicuota_para_monto_fijo: Decimal — Alic para despejar neto desde TTC (default alicuota_iva).
    """
    validar_lista_precio(lista_id)

    # [SPEC B.5] Promoción Monto fijo — retorno es precio final TTC (antes de cortar por precio_base==0)
    if kwargs.get("promo_tipo") == "Monto fijo":
        prom = kwargs.get("promo_porc")
        if prom is None:
            raise ValueError("promo_tipo=Monto fijo requiere promo_porc")
        return _q2(Decimal(prom))

    # [SPEC D] Cliente sin tipo asignado → no aplicar descuento pasado como cliente
    if "tipo_cliente" in kwargs and kwargs["tipo_cliente"] is None:
        descuento_cliente = Decimal("0")

    if precio_base == 0:
        return Decimal("0.00")

    desc = normalizar_descuento_porcentual(Decimal(descuento_cliente))
    # [SPEC B.4] Regla Descuento vs desc_renglon: max o forzar según prioridad_regla
    if kwargs.get("descuento_regla_pct") is not None:
        dr = normalizar_descuento_porcentual(Decimal(kwargs["descuento_regla_pct"]))
        if kwargs.get("prioridad_regla", "Desc. Cliente") != "Desc. Cliente":
            desc = dr
        else:
            desc = max(desc, dr)

    neto = precio_base - (precio_base * desc / Decimal("100"))
    neto = _q2(neto)

    incluir_iva = bool(kwargs.get("incluir_iva", False))
    if not incluir_iva:
        return neto

    alicuota_iva = Decimal(kwargs.get("alicuota_iva", "21"))
    imp_interno = Decimal(kwargs.get("impuesto_interno_pct", "0"))
    # [SPEC B.4] IVA e interno sobre neto tras descuento
    iva = neto * alicuota_iva / Decimal("100")
    interno = neto * imp_interno / Decimal("100")
    final = neto + iva + interno
    return _q2(final)


def calcular_neto_desde_monto_fijo_ttc(
    precio_neto_referencia: Decimal,
    promo_porc_ttc: Decimal,
    alicuota_iva: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    [SPEC B.5] Monto fijo: neto_calc redondeado 4 dec, desc_final 1 dec (como PHP).
    Retorna (precio_neto_calc, desc_final_pct, precio_venta_final_ttc).
    """
    alic = alicuota_iva
    precio_neto_calc = (
        promo_porc_ttc / (Decimal("1") + alic / Decimal("100"))
    ).quantize(Q4, rounding=ROUND_HALF_UP)
    if precio_neto_referencia == 0:
        desc_final = Decimal("0.0")
    else:
        desc_final = (
            (precio_neto_referencia - precio_neto_calc)
            * Decimal("100")
            / precio_neto_referencia
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return precio_neto_calc, desc_final, _q2(promo_porc_ttc)
