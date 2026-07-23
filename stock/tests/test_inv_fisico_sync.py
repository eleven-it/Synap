# -*- coding: utf-8 -*-
"""Tests sync batch inventario físico (Fase 3 — Strict TDD)."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from stock.services import inventario_fisico as svc


class EvaluarEventoSyncPuroTest(SimpleTestCase):
    def test_mismo_contador_siempre_aceptado_lww(self):
        linea = {"id_contador": 5, "cantidad_contada": Decimal("10")}
        resultado = svc.evaluar_resultado_evento_sync(
            linea_actual=linea,
            id_contador=5,
            cantidad=Decimal("15"),
        )
        self.assertEqual(resultado, svc.RESULTADO_ACEPTADO)

    def test_distintos_contadores_cantidades_distintas_conflicto(self):
        linea = {"id_contador": 5, "cantidad_contada": Decimal("10")}
        resultado = svc.evaluar_resultado_evento_sync(
            linea_actual=linea,
            id_contador=8,
            cantidad=Decimal("12"),
        )
        self.assertEqual(resultado, svc.RESULTADO_CONFLICTO)

    def test_linea_vacia_aceptada(self):
        self.assertEqual(
            svc.evaluar_resultado_evento_sync(None, 3, Decimal("1")),
            svc.RESULTADO_ACEPTADO,
        )


class SyncEventosServiceTest(SimpleTestCase):
    def _campana_en_conteo(self):
        return {
            "id_campana": 1,
            "estado": svc.ESTADO_EN_CONTEO,
            "contadores_json": json.dumps([10]),
        }

    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_client_event_id_duplicado_idempotente(
        self, mock_cursor_ctx, mock_obtener_campana
    ):
        mock_obtener_campana.return_value = self._campana_en_conteo()
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "client_event_id": "evt-1",
            "resultado": svc.RESULTADO_ACEPTADO,
        }
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        eventos = [
            {
                "client_event_id": "evt-1",
                "id_articulo": 100,
                "id_deposito": 3,
                "cantidad": "5",
                "client_ts": "2026-07-23 10:00:00",
            }
        ]
        resp = svc.sync_eventos("emp", 1, eventos, id_usuario=10)
        self.assertEqual(len(resp["aceptados"]), 1)
        self.assertEqual(resp["conflictos"], [])
        self.assertEqual(resp["rechazados"], [])

    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_batch_clasifica_aceptados_conflictos_rechazados(
        self, mock_cursor_ctx, mock_obtener_campana
    ):
        campana = self._campana_en_conteo()
        campana["contadores_json"] = json.dumps([10, 20])
        mock_obtener_campana.return_value = campana

        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            None,
            {"id_linea": 1, "id_contador": 10, "cantidad_contada": Decimal("10"), "saldo_snapshot": Decimal("10")},
            None,
            None,
        ]
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        eventos = [
            {
                "client_event_id": "evt-conflicto",
                "id_articulo": 100,
                "id_deposito": 3,
                "cantidad": "12",
                "client_ts": "2026-07-23 10:01:00",
            },
            {
                "client_event_id": "evt-rechazo",
                "id_articulo": 999,
                "id_deposito": 3,
                "cantidad": "1",
                "client_ts": "2026-07-23 10:02:00",
            },
        ]
        resp = svc.sync_eventos("emp", 1, eventos, id_usuario=20)
        self.assertEqual(len(resp["conflictos"]), 1)
        self.assertEqual(len(resp["rechazados"]), 1)
        self.assertIn("motivo", resp["conflictos"][0])
        self.assertIn("motivo", resp["rechazados"][0])

    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_operario_no_asignado_rechazado(self, mock_obtener_campana):
        mock_obtener_campana.return_value = {
            "id_campana": 1,
            "estado": svc.ESTADO_EN_CONTEO,
            "contadores_json": json.dumps([99]),
            "depositos": [3],
        }

        eventos = [
            {
                "client_event_id": "evt-x",
                "id_articulo": 1,
                "id_deposito": 3,
                "cantidad": "1",
                "client_ts": "2026-07-23 10:00:00",
            }
        ]
        resp = svc.sync_eventos("emp", 1, eventos, id_usuario=10)
        self.assertEqual(len(resp["rechazados"]), 1)
        self.assertIn("asignación", resp["rechazados"][0]["motivo"].lower())
