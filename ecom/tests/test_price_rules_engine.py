from decimal import Decimal

from ecom.services.price_rules_engine import (
    PromocionArticulo,
    ReglaPrecio,
    calcular_precio_con_motor,
    resolver_promocion_articulo,
)


def test_resolver_promocion_articulo_por_lista_y_vigencia():
    art = {
        "promocion": "Si",
        "promocion_lista1": "Si",
        "promocion_tipo": "Monto fijo",
        "promocion_por": "121.00",
        "promocion_cant": 1,
        "promocion_vigencia_desde": None,
        "promocion_vigencia_hasta": None,
    }
    promo = resolver_promocion_articulo(art, lista_id=1)
    assert promo is not None
    assert promo.promo_tipo == "Monto fijo"
    assert promo.promo_por == Decimal("121.00")


def test_motor_aplica_regla_descuento():
    r = calcular_precio_con_motor(
        precio_base=Decimal("1000"),
        lista_id=1,
        descuento_cliente=Decimal("10"),
        alicuota_iva=Decimal("21"),
        impuesto_interno_pct=Decimal("0"),
        incluir_iva=True,
        tipo_cliente="Minorista",
        regla=ReglaPrecio(tipo_calculo="Descuento", importe_regla=Decimal("20")),
        promo=None,
    )
    assert r == Decimal("968.00")


def test_motor_aplica_promo_monto_fijo():
    r = calcular_precio_con_motor(
        precio_base=Decimal("1000"),
        lista_id=1,
        descuento_cliente=Decimal("10"),
        alicuota_iva=Decimal("21"),
        impuesto_interno_pct=Decimal("0"),
        incluir_iva=True,
        tipo_cliente="Minorista",
        regla=None,
        promo=PromocionArticulo(promo_tipo="Monto fijo", promo_por=Decimal("242.00"), promo_cant=1),
    )
    assert r == Decimal("242.00")


def test_motor_aplica_promo_monto_fijo_con_iva_no_devuelve_neto():
    r = calcular_precio_con_motor(
        precio_base=Decimal("1000"),
        lista_id=1,
        descuento_cliente=Decimal("10"),
        alicuota_iva=Decimal("21"),
        impuesto_interno_pct=Decimal("0"),
        incluir_iva=False,
        tipo_cliente="Minorista",
        regla=None,
        promo=PromocionArticulo(promo_tipo="Monto fijo", promo_por=Decimal("242.00"), promo_cant=1),
    )
    assert r == Decimal("200.00")


def test_motor_promocion_cantidad_intervalo_no_pisa_descuento_cliente():
    r = calcular_precio_con_motor(
        precio_base=Decimal("1000"),
        lista_id=1,
        descuento_cliente=Decimal("10"),
        alicuota_iva=Decimal("21"),
        impuesto_interno_pct=Decimal("0"),
        incluir_iva=True,
        tipo_cliente="Minorista",
        regla=None,
        promo=PromocionArticulo(promo_tipo="Cantidad - Intervalo", promo_por=Decimal("50"), promo_cant=3),
    )
    assert r == Decimal("1089.00")


def test_motor_precio_fijo_regla_sin_descuento_adicional():
    r = calcular_precio_con_motor(
        precio_base=Decimal("1000"),
        lista_id=1,
        descuento_cliente=Decimal("20"),
        alicuota_iva=Decimal("21"),
        impuesto_interno_pct=Decimal("0"),
        incluir_iva=False,
        tipo_cliente="Minorista",
        regla=ReglaPrecio(tipo_calculo="Precio fijo", importe_regla=Decimal("400")),
        promo=None,
    )
    assert r == Decimal("400.00")
