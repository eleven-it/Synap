"""
Integración básica del motor de reglas/promos con MySQL legacy.
"""

from decimal import Decimal

import pytest

from ecom.services.price_rules_engine import (
    calcular_precio_con_motor,
    resolver_promocion_articulo,
    resolver_regla_precio,
)


@pytest.mark.integration
class TestPriceRulesEngineIntegration:
    def test_resolver_regla_no_explota(self, legacy_db_connection):
        with legacy_db_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT IDArt, CodigoProveedor, CodigoRubro, IDSubRubro
                FROM articulo
                WHERE tipo_art = 'Articulo'
                LIMIT 1
                """
            )
            row = cursor.fetchone()
        if not row:
            pytest.skip("Base sin artículos para test integración")

        art = {
            "IDArt": row[0],
            "CodigoProveedor": row[1],
            "CodigoRubro": row[2],
            "IDSubRubro": row[3],
        }
        regla = resolver_regla_precio(legacy_db_connection, art, codigo_cliente=1)
        assert regla is None or hasattr(regla, "tipo_calculo")

    def test_promocion_y_motor_fallback(self):
        art = {
            "promocion": "Si",
            "promocion_lista1": "Si",
            "promocion_tipo": "Importe descuento",
            "promocion_por": "15",
            "promocion_cant": 1,
            "promocion_vigencia_desde": None,
            "promocion_vigencia_hasta": None,
        }
        promo = resolver_promocion_articulo(art, lista_id=1)
        assert promo is not None
        precio = calcular_precio_con_motor(
            precio_base=Decimal("1000"),
            lista_id=1,
            descuento_cliente=Decimal("10"),
            alicuota_iva=Decimal("21"),
            impuesto_interno_pct=Decimal("0"),
            incluir_iva=True,
            tipo_cliente="Minorista",
            regla=None,
            promo=promo,
        )
        assert precio == Decimal("1028.50")
