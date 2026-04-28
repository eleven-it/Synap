"""Tests unitarios del calculador de precios (SPEC_PRECIOS.md B, D, E)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from ecom.services.price_calculator import (
    ListaPrecioInvalidaError,
    calcular_neto_desde_monto_fijo_ttc,
    calcular_precio,
    normalizar_descuento_porcentual,
    vigencia_promo,
)
from ecom.tests.factories import ArticuloFactory, ClienteFactory, ListaPrecioFactory


class TestCalcularPrecioBase:
    def test_precio_sin_descuento(self):
        r = calcular_precio(Decimal("1000.00"), 1, Decimal("0"))
        assert r == Decimal("1000.00")

    def test_descuento_porcentual(self):
        r = calcular_precio(Decimal("1000.00"), 1, Decimal("10"))
        assert r == Decimal("900.00")

    def test_precio_cero_retorna_cero(self):
        assert calcular_precio(Decimal("0"), 3, Decimal("15")) == Decimal("0.00")

    def test_lista_inexistente_raise(self):
        with pytest.raises(ListaPrecioInvalidaError):
            calcular_precio(Decimal("100"), 99, Decimal("0"))

    def test_sin_descuento_con_iva_tabla_e(self):
        # [SPEC E] Sin descuento, IVA 21%, interno 0
        r = calcular_precio(
            Decimal("1000.00"),
            1,
            Decimal("0"),
            incluir_iva=True,
            alicuota_iva=Decimal("21"),
            impuesto_interno_pct=Decimal("0"),
        )
        assert r == Decimal("1210.00")

    def test_descuento_10_con_iva_tabla_e(self):
        r = calcular_precio(
            Decimal("1000.00"),
            1,
            Decimal("10"),
            incluir_iva=True,
            alicuota_iva=Decimal("21"),
        )
        assert r == Decimal("1089.00")

    def test_lista_oficial_id_6_valida(self):
        r = calcular_precio(Decimal("500.00"), 6, Decimal("0"))
        assert r == Decimal("500.00")

    def test_articulo_factory_alimenta_precio_base(self):
        art = ArticuloFactory(precio_base_lista=Decimal("2500.50"))
        assert art.lista_activa_id == 1
        r = calcular_precio(art.precio_base_lista, art.lista_activa_id, Decimal("0"))
        assert r == Decimal("2500.50")


class TestRedondeo:
    def test_redondeo_half_up(self):
        # 10.005 -> 10.01 con 2 decimales en neto tras descuento 0
        r = calcular_precio(Decimal("10.005"), 1, Decimal("0"))
        assert r == Decimal("10.01")

    def test_precision_dos_decimales(self):
        # Descuento >100% se capa a 100% → neto 0
        r = calcular_precio(Decimal("1000.00"), 1, Decimal("100.01"))
        assert r == Decimal("0.00")


class TestCasosBorde:
    def test_descuento_mayor_100(self):
        assert calcular_precio(Decimal("100.00"), 1, Decimal("150")) == Decimal("0.00")

    def test_cliente_sin_tipo(self):
        assert calcular_precio(
            Decimal("1000.00"),
            1,
            Decimal("25"),
            tipo_cliente=None,
        ) == Decimal("1000.00")

    def test_descuento_negativo_tratado_como_cero(self):
        assert normalizar_descuento_porcentual(Decimal("-5")) == Decimal("0")


class TestReglaVsDescuentoCliente:
    def test_prioridad_no_desc_cliente_fuerza_regla(self):
        r = calcular_precio(
            Decimal("1000.00"),
            1,
            Decimal("20"),
            descuento_regla_pct=Decimal("10"),
            prioridad_regla="General",
            incluir_iva=True,
            alicuota_iva=Decimal("21"),
        )
        # Regla 10%: neto 900 -> 1089.00
        assert r == Decimal("1089.00")

    def test_prioridad_desc_cliente_toma_max(self):
        r = calcular_precio(
            Decimal("1000.00"),
            1,
            Decimal("20"),
            descuento_regla_pct=Decimal("10"),
            prioridad_regla="Desc. Cliente",
            incluir_iva=True,
            alicuota_iva=Decimal("21"),
        )
        # max(20,10)=20%: neto 800 -> 968.00
        assert r == Decimal("968.00")


class TestPromoMontoFijo:
    def test_promo_monto_fijo_devuelve_ttc(self):
        r = calcular_precio(
            Decimal("1000.00"),
            1,
            Decimal("0"),
            promo_tipo="Monto fijo",
            promo_porc=Decimal("121.00"),
        )
        assert r == Decimal("121.00")

    def test_promo_monto_fijo_sin_promo_porc_raise(self):
        with pytest.raises(ValueError, match="promo_porc"):
            calcular_precio(Decimal("1"), 1, Decimal("0"), promo_tipo="Monto fijo")


class TestCalcularNetoDesdeMontoFijo:
    def test_tabla_e_monto_fijo(self):
        neto_c, desc_p, ttc = calcular_neto_desde_monto_fijo_ttc(
            Decimal("1000.00"),
            Decimal("121.00"),
            Decimal("21"),
        )
        assert ttc == Decimal("121.00")
        assert neto_c == Decimal("100.0000")
        assert desc_p == Decimal("90.0")

    def test_precio_referencia_cero_desc_cero(self):
        _, desc_p, _ = calcular_neto_desde_monto_fijo_ttc(
            Decimal("0"),
            Decimal("121.00"),
            Decimal("21"),
        )
        assert desc_p == Decimal("0.0")


class TestVigenciaPromo:
    def test_ambas_nulas_vigente(self):
        assert vigencia_promo(None, None) is True

    def test_rango_incluye_hoy(self):
        d0 = date.today() - timedelta(days=1)
        d1 = date.today() + timedelta(days=1)
        assert vigencia_promo(d0, d1) is True

    def test_anio_hasta_mayor_2038(self):
        assert vigencia_promo(date(2020, 1, 1), "2039-12-31") is True

    def test_solo_hasta(self):
        assert vigencia_promo(None, date.today() + timedelta(days=1)) is True
        assert vigencia_promo(None, date.today() - timedelta(days=1)) is False

    def test_solo_desde(self):
        assert vigencia_promo(date.today() - timedelta(days=1), None) is True
        assert vigencia_promo(date.today() + timedelta(days=1), None) is False

    def test_fechas_como_string(self):
        assert vigencia_promo("2020-01-01", "2099-12-31") is True

    def test_fechas_datetime(self):
        assert (
            vigencia_promo(
                datetime(2020, 1, 1, 10, 0, 0), datetime(2099, 12, 31, 23, 59, 59)
            )
            is True
        )


class TestImpuestoInternoEnFinal:
    def test_iva_e_interno_sobre_neto(self):
        r = calcular_precio(
            Decimal("1000.00"),
            1,
            Decimal("0"),
            incluir_iva=True,
            alicuota_iva=Decimal("21"),
            impuesto_interno_pct=Decimal("2"),
        )
        assert r == Decimal("1230.00")


class TestFactoriesMemoria:
    def test_lista_precio_factory(self):
        lp = ListaPrecioFactory.build(id=3)
        assert lp.id == 3
        assert "Lista" in lp.etiqueta

    def test_cliente_factory(self):
        c = ClienteFactory.build(tipo_cliente=None)
        assert c.tipo_cliente is None
