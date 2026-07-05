"""
Tests repositorios MPR en MySQL (mpr_envio_produccion, mpr_config).

Requiere tablas core aplicadas en la BD de prueba:
  docker exec Synap_app python manage.py apply_mpr_core_tables administranet93
"""
from decimal import Decimal

from django.test import TestCase

from mpr.repositories.config import actualizar_bloqueo_fabricando, obtener_config
from mpr.repositories.envio_produccion import crear_envios_lote, sumar_envios_por_componente
from mpr.services import _query_enviado_tablero_componente, enviar_a_produccion_lote

MYSQL_EMPRESA = "administranet93"
ART_TEST = 999001


class TestEnvioProduccionRepositoryMySQL(TestCase):
    """Ledger envíos en mpr_envio_produccion."""

    def setUp(self):
        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA) as c:
            c.execute(
                "DELETE FROM mpr_envio_produccion WHERE id_articulo = %s",
                [ART_TEST],
            )

    def tearDown(self):
        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA) as c:
            c.execute(
                "DELETE FROM mpr_envio_produccion WHERE id_articulo = %s",
                [ART_TEST],
            )

    def test_crear_y_sumar_envios(self):
        n = crear_envios_lote(
            MYSQL_EMPRESA,
            1,
            [(ART_TEST, Decimal("10")), (ART_TEST, Decimal("5"))],
        )
        self.assertEqual(n, 2)
        tot = sumar_envios_por_componente(MYSQL_EMPRESA, [ART_TEST])
        self.assertEqual(tot.get(ART_TEST), Decimal("15"))

    def test_servicio_enviar_lote_mysql(self):
        ok, n, warnings, err = enviar_a_produccion_lote(
            MYSQL_EMPRESA,
            1,
            [(ART_TEST, Decimal("7"))],
        )
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(n, 1)
        q = _query_enviado_tablero_componente(MYSQL_EMPRESA, [ART_TEST])
        self.assertEqual(q.get(ART_TEST), Decimal("7"))


class TestMprConfigRepositoryMySQL(TestCase):
    def test_actualizar_y_leer_bloqueo(self):
        ok, err = actualizar_bloqueo_fabricando(MYSQL_EMPRESA, False)
        self.assertTrue(ok)
        self.assertIsNone(err)
        cfg = obtener_config(MYSQL_EMPRESA)
        self.assertFalse(cfg["bloquear_parte_supera_fabricando"])
        actualizar_bloqueo_fabricando(MYSQL_EMPRESA, True)
        cfg2 = obtener_config(MYSQL_EMPRESA)
        self.assertTrue(cfg2["bloquear_parte_supera_fabricando"])
