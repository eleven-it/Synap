"""Regresión numérica — tabla SPEC_PRECIOS.md sección E y casos base."""

from decimal import Decimal

import pytest

from ecom.services.price_calculator import calcular_precio

# (descripcion, precio_base, lista_id, descuento, esperado, kwargs)
CASOS_PARIDAD = [
    ("sin descuento neto", Decimal("1000.00"), 1, Decimal("0"), Decimal("1000.00"), {}),
    ("descuento 10% neto", Decimal("1000.00"), 1, Decimal("10"), Decimal("900.00"), {}),
    (
        "sin descuento con IVA 21%",
        Decimal("1000.00"),
        1,
        Decimal("0"),
        Decimal("1210.00"),
        {"incluir_iva": True, "alicuota_iva": Decimal("21")},
    ),
    (
        "descuento 10% con IVA 21%",
        Decimal("1000.00"),
        1,
        Decimal("10"),
        Decimal("1089.00"),
        {"incluir_iva": True, "alicuota_iva": Decimal("21")},
    ),
    (
        "lista 5 neto",
        Decimal("500.00"),
        5,
        Decimal("0"),
        Decimal("500.00"),
        {},
    ),
    (
        "lista oficial id 6",
        Decimal("750.00"),
        6,
        Decimal("5"),
        Decimal("712.50"),
        {},
    ),
]


@pytest.mark.parametrize(
    "desc,precio_base,lista_id,descuento,esperado,extra", CASOS_PARIDAD
)
def test_paridad_numerica(desc, precio_base, lista_id, descuento, esperado, extra):
    resultado = calcular_precio(precio_base, lista_id, descuento, **extra)
    assert (
        resultado == esperado
    ), f"Caso '{desc}': esperado {esperado}, obtuvo {resultado}"
