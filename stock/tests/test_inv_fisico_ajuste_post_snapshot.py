# -*- coding: utf-8 -*-
"""Tests ajuste post-snapshot inventario físico (funciones puras y recalc)."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from stock.services import inventario_fisico as svc


class FuncionesPurasAjustePostSnapshotTest(SimpleTestCase):
    def test_ajuste_efectivo_usa_manual_si_existe(self):
        self.assertEqual(
            svc.ajuste_efectivo(Decimal("5"), Decimal("-2")),
            Decimal("-2"),
        )

    def test_ajuste_efectivo_sistema_si_manual_none(self):
        self.assertEqual(
            svc.ajuste_efectivo(Decimal("3.5"), None),
            Decimal("3.5"),
        )

    def test_ajuste_efectivo_cero_si_ambos_none(self):
        self.assertEqual(svc.ajuste_efectivo(None, None), Decimal("0"))

    def test_calcular_disponible_ajustado(self):
        self.assertEqual(
            svc.calcular_disponible_ajustado(Decimal("100"), Decimal("7")),
            Decimal("107"),
        )

    def test_calcular_diferencia_real_contado_menos_disponible(self):
        self.assertEqual(
            svc.calcular_diferencia_real(Decimal("12"), Decimal("10")),
            Decimal("2"),
        )

    def test_calcular_diferencia_real_none_si_no_contado(self):
        self.assertIsNone(svc.calcular_diferencia_real(None, Decimal("10")))

    def test_hay_descuadre_true_si_saldo_ref_difiere(self):
        self.assertTrue(
            svc.hay_descuadre(
                saldo_snapshot=Decimal("10"),
                ajuste_sistema=Decimal("3"),
                saldo_actual_ref=Decimal("14"),
            )
        )

    def test_hay_descuadre_false_si_coincide(self):
        self.assertFalse(
            svc.hay_descuadre(
                saldo_snapshot=Decimal("10"),
                ajuste_sistema=Decimal("3"),
                saldo_actual_ref=Decimal("13"),
            )
        )

    def test_hay_descuadre_false_si_ref_none(self):
        self.assertFalse(
            svc.hay_descuadre(
                saldo_snapshot=Decimal("10"),
                ajuste_sistema=Decimal("3"),
                saldo_actual_ref=None,
            )
        )


class RecalcularAjustePostSnapshotTest(SimpleTestCase):
    def _campana_en_revision(self):
        return {
            "id_campana": 7,
            "estado": svc.ESTADO_EN_REVISION,
            "fecha_snapshot": "2026-08-04 08:00:00",
            "depositos": [3],
        }

    @patch("stock.services.inventario_fisico._fetch_saldos_deposito")
    @patch("stock.services.inventario_fisico.calcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_recalc_preserva_override_sin_pisar(
        self, mock_cursor_ctx, mock_obtener, mock_calcular, mock_saldos
    ):
        mock_obtener.return_value = self._campana_en_revision()
        mock_calcular.return_value = {(100, 3): Decimal("5")}
        mock_saldos.return_value = {3: Decimal("23")}

        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        lineas_db = [
            {
                "id_linea": 1,
                "id_articulo": 100,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("20"),
                "ajuste_manual": Decimal("8"),
            }
        ]
        cursor.fetchall.side_effect = [lineas_db]

        ok, result = svc.recalcular_ajuste_post_snapshot(
            "emp", 7, id_usuario=1, pisar_overrides=False
        )

        self.assertTrue(ok, result)
        self.assertEqual(result["lineas_actualizadas"], 1)
        self.assertEqual(result["overrides_pisados"], 0)

        update_sql = cursor.execute.call_args_list[-1].args[0]
        self.assertIn("ajuste_calculado_at = NOW()", update_sql)
        self.assertNotIn("ajuste_manual = NULL", update_sql)

        params = cursor.execute.call_args_list[-1].args[1]
        ajuste_sys, saldo_ref, diff_real, _id_linea = params
        self.assertEqual(ajuste_sys, Decimal("5"))
        self.assertEqual(saldo_ref, Decimal("23"))
        # contado 20 - (snapshot 10 + override 8) = 2
        self.assertEqual(diff_real, Decimal("2"))

    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._fetch_saldos_deposito")
    @patch("stock.services.inventario_fisico.calcular_ajuste_post_snapshot")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_recalc_pisa_override_con_flag(
        self, mock_cursor_ctx, mock_obtener, mock_calcular, mock_saldos, mock_auditoria
    ):
        mock_obtener.return_value = self._campana_en_revision()
        mock_calcular.return_value = {(100, 3): Decimal("5")}
        mock_saldos.return_value = {3: Decimal("15")}

        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        lineas_db = [
            {
                "id_linea": 1,
                "id_articulo": 100,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("20"),
                "ajuste_manual": Decimal("8"),
            }
        ]
        cursor.fetchall.side_effect = [lineas_db]

        ok, result = svc.recalcular_ajuste_post_snapshot(
            "emp", 7, id_usuario=9, pisar_overrides=True
        )

        self.assertTrue(ok, result)
        self.assertEqual(result["overrides_pisados"], 1)
        mock_auditoria.assert_called_once()

        update_sql = cursor.execute.call_args_list[-1].args[0]
        self.assertIn("ajuste_manual = NULL", update_sql)

        params = cursor.execute.call_args_list[-1].args[1]
        _ajuste_sys, _saldo_ref, diff_real, _id_linea = params
        # contado 20 - (snapshot 10 + sistema 5) = 5
        self.assertEqual(diff_real, Decimal("5"))

    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_recalc_omitido_estado_final(self, mock_obtener):
        mock_obtener.return_value = {
            "id_campana": 7,
            "estado": svc.ESTADO_APLICADO,
        }
        ok, result = svc.recalcular_ajuste_post_snapshot(
            "emp", 7, id_usuario=1, pisar_overrides=False
        )
        self.assertTrue(ok)
        self.assertTrue(result.get("omitido"))
