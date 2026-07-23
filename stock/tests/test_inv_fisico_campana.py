# -*- coding: utf-8 -*-
"""Tests campaña inventario físico (Fase 2 — Strict TDD)."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.urls import reverse

from stock.services import inventario_fisico as svc


class TiposMprElegiblesTest(SimpleTestCase):
    def test_terminado_semi_y_2da_son_elegibles(self):
        for tipo in ("Terminado", "SemiElaborado", "2daSeleccion"):
            self.assertTrue(svc.es_tipo_mpr_elegible(tipo))

    def test_produccion_no_es_elegible(self):
        self.assertFalse(svc.es_tipo_mpr_elegible("Produccion"))
        self.assertFalse(svc.es_tipo_mpr_elegible(""))
        self.assertFalse(svc.es_tipo_mpr_elegible(None))


class CalcularDiferenciaTest(SimpleTestCase):
    def test_diferencia_positiva_sobrante(self):
        self.assertEqual(svc.calcular_diferencia(Decimal("15"), Decimal("10")), Decimal("5"))

    def test_diferencia_negativa_faltante(self):
        self.assertEqual(svc.calcular_diferencia(Decimal("8"), Decimal("12")), Decimal("-4"))

    def test_contado_none_es_cero(self):
        self.assertEqual(svc.calcular_diferencia(None, Decimal("3")), Decimal("-3"))


class TransicionesEstadoTest(SimpleTestCase):
    def test_borrador_a_en_conteo(self):
        self.assertTrue(svc.transicion_estado_permitida(svc.ESTADO_BORRADOR, svc.ESTADO_EN_CONTEO))

    def test_borrador_no_a_aplicado(self):
        self.assertFalse(svc.transicion_estado_permitida(svc.ESTADO_BORRADOR, svc.ESTADO_APLICADO))

    def test_en_conteo_a_en_revision(self):
        self.assertTrue(svc.transicion_estado_permitida(svc.ESTADO_EN_CONTEO, svc.ESTADO_EN_REVISION))

    def test_en_revision_reconteo_a_en_conteo(self):
        self.assertTrue(svc.transicion_estado_permitida(svc.ESTADO_EN_REVISION, svc.ESTADO_EN_CONTEO))

    def test_aplicado_es_terminal(self):
        self.assertFalse(svc.transicion_estado_permitida(svc.ESTADO_APLICADO, svc.ESTADO_ANULADO))


class AsignacionContadoresTest(SimpleTestCase):
    def test_usuario_asignado_puede_contar(self):
        campana = {"contadores_json": json.dumps([10, 20])}
        self.assertTrue(svc.usuario_asignado_a_campana(campana, 10))

    def test_usuario_no_asignado_bloqueado(self):
        campana = {"contadores_json": json.dumps([10])}
        self.assertFalse(svc.usuario_asignado_a_campana(campana, 99))


class CrearCampanaServiceTest(SimpleTestCase):
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_crear_campana_rechaza_deposito_no_mpr(self, mock_cursor_ctx):
        cursor = MagicMock()
        tablas = [{"Tables_in_x": "deposito"}]
        cursor.fetchall.return_value = tablas
        cursor.fetchone.return_value = {
            "CodDeposito": 5,
            "tipo_mpr": "Produccion",
            "suma_stock": "Si",
        }
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.crear_campana(
            "empresa_test",
            fecha="2026-07-23",
            depositos_ids=[5],
            id_usuario_alta=1,
        )
        self.assertFalse(ok)
        self.assertIn("elegible", result.get("error", "").lower())

    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_crear_campana_inserta_lineas_snapshot(self, mock_cursor_ctx):
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "CodDeposito": 3,
            "tipo_mpr": "Terminado",
            "suma_stock": "Si",
        }
        cursor.lastrowid = 42
        tablas = [{"Tables_in_x": "deposito"}, {"Tables_in_x": "stock_deposito"}]
        cursor.fetchall.side_effect = [
            tablas,
            tablas,
            [{"id_articulo": 100, "saldo": Decimal("7.0000")}],
        ]
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.crear_campana(
            "empresa_test",
            fecha="2026-07-23",
            depositos_ids=[3],
            id_usuario_alta=7,
        )
        self.assertTrue(ok, result)
        self.assertEqual(result["id_campana"], 42)
        self.assertEqual(result["estado"], svc.ESTADO_BORRADOR)
        inserts = [c.args[0] for c in cursor.execute.call_args_list if c.args]
        linea_inserts = [s for s in inserts if "inv_fisico_linea" in s and "INSERT" in s.upper()]
        self.assertEqual(len(linea_inserts), 1)
        self.assertIn("saldo_snapshot", linea_inserts[0])


class InventarioPivoteIntactoTest(SimpleTestCase):
    """2.4 — consulta pivote /stock/inventario/ no se confunde con inventario físico."""

    def test_reverse_inventario_consulta_pivote_existe(self):
        self.assertEqual(reverse("stock:inventario"), "/stock/inventario/")

    def test_reverse_inventario_fisico_es_ruta_distinta(self):
        self.assertEqual(reverse("stock:inventario_fisico_list"), "/stock/inventario-fisico/")
        self.assertNotEqual(reverse("stock:inventario"), reverse("stock:inventario_fisico_list"))

    def test_nombres_url_distinguen_consulta_y_fisico(self):
        self.assertIn("inventario-fisico", reverse("stock:inventario_fisico_list"))
        self.assertNotIn("inventario-fisico", reverse("stock:inventario"))
