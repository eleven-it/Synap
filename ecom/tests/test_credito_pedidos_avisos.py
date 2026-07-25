# -*- coding: utf-8 -*-
"""Avisos cobranza: plantillas, EcomMailQueue y dedup SLA (Fase B)."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from ecom.models import EcomMailQueue
from ecom.services.credito_pedidos.avisos import (
    TIPO_PEDIDO_BLOQUEADO,
    debe_encolar_aviso,
    encolar_aviso_credito,
    renderizar_plantilla,
)


class TestRenderPlantilla(unittest.TestCase):
    def test_sustituye_variables(self):
        asunto, cuerpo = renderizar_plantilla(
            "Pedido {{nro_comprobante}} bloqueado",
            "Cliente {{nombre_cliente}} — monto {{importe}}",
            {
                "nro_comprobante": "0001-00000100",
                "nombre_cliente": "ACME",
                "importe": "15000.00",
            },
        )
        self.assertIn("0001-00000100", asunto)
        self.assertIn("ACME", cuerpo)
        self.assertIn("15000.00", cuerpo)


class TestDedupAvisos(unittest.TestCase):
    @patch("ecom.services.credito_pedidos.avisos.credito_pedidos_activo", return_value=True)
    def test_pedido_bloqueado_dedup_por_cod_mov(self, _flag):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"cnt": 1}
        dup = debe_encolar_aviso(
            cursor,
            "emp1",
            id_cliente=10,
            tipo_aviso=TIPO_PEDIDO_BLOQUEADO,
            canal="PED",
            codigo_movimiento=9001,
        )
        self.assertFalse(dup)
        sql = str(cursor.execute.call_args[0][0]).lower()
        self.assertIn("codigo_movimiento", sql)

    @patch("ecom.services.credito_pedidos.avisos.credito_pedidos_activo", return_value=True)
    @patch("ecom.services.credito_pedidos.avisos.credito_aviso_sla_horas", return_value=24)
    def test_sla_24h_por_cliente_tipo(self, _sla, _flag):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"cnt": 1}
        dup = debe_encolar_aviso(
            cursor,
            "emp1",
            id_cliente=10,
            tipo_aviso="cobranza",
            canal="PED",
            codigo_movimiento=None,
        )
        self.assertFalse(dup)


class TestEncolarAviso(unittest.TestCase):
    def test_crea_fila_mail_queue(self):
        with patch("ecom.services.credito_pedidos.avisos.EcomMailQueue.objects.create") as mock_create:
            mock_create.return_value = MagicMock(id=1)
            item = encolar_aviso_credito(
                base_empresa="emp1",
                to_email="cobranzas@test.com",
                asunto="Aviso",
                cuerpo="Cuerpo",
                payload={"codigo_movimiento": 9001},
            )
            mock_create.assert_called_once()
            kwargs = mock_create.call_args.kwargs
            self.assertEqual(kwargs["base_empresa"], "emp1")
            self.assertEqual(kwargs["to_email"], "cobranzas@test.com")
            self.assertEqual(kwargs["subject"], "Aviso")
