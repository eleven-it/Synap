# -*- coding: utf-8 -*-
"""Tests helpers configuracion_ecom workflow crédito pedidos (Fase 0)."""
from unittest.mock import patch

from django.test import SimpleTestCase

from ecom.services.ecom_config_mysql import (
    KEY_CREDITO_AVISO_SLA_HORAS,
    KEY_CREDITO_HOLD_PREP,
    KEY_CREDITO_PEDIDOS_ACTIVA,
    credito_aviso_sla_horas,
    credito_hold_prep_activo,
    credito_pedidos_activo,
)


class CreditoPedidosConfigTests(SimpleTestCase):
    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_master_default_no(self, mock_leer):
        mock_leer.return_value = "No"
        self.assertFalse(credito_pedidos_activo("emp1"))
        mock_leer.assert_called_with("emp1", KEY_CREDITO_PEDIDOS_ACTIVA, "No")

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_master_si_activo(self, mock_leer):
        mock_leer.return_value = "Si"
        self.assertTrue(credito_pedidos_activo("emp1"))

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_hold_subflag_ignorado_si_master_no(self, mock_leer):
        def side_effect(base, key, default=""):
            if key == KEY_CREDITO_PEDIDOS_ACTIVA:
                return "No"
            if key == KEY_CREDITO_HOLD_PREP:
                return "Si"
            return default

        mock_leer.side_effect = side_effect
        self.assertFalse(credito_hold_prep_activo("emp1"))

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_hold_activo_si_master_si(self, mock_leer):
        def side_effect(base, key, default=""):
            if key == KEY_CREDITO_PEDIDOS_ACTIVA:
                return "Si"
            if key == KEY_CREDITO_HOLD_PREP:
                return "Si"
            return default

        mock_leer.side_effect = side_effect
        self.assertTrue(credito_hold_prep_activo("emp1"))

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_sla_default_24_si_falta_fila(self, mock_leer):
        mock_leer.return_value = ""
        self.assertEqual(credito_aviso_sla_horas("emp1"), 24)
        mock_leer.assert_called_with("emp1", KEY_CREDITO_AVISO_SLA_HORAS, "24")

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_sla_parsea_entero_valido(self, mock_leer):
        mock_leer.return_value = "48"
        self.assertEqual(credito_aviso_sla_horas("emp1"), 48)

    @patch("ecom.services.ecom_config_mysql.leer_valor_configuracion_ecom")
    def test_sla_invalido_vuelve_a_24(self, mock_leer):
        mock_leer.return_value = "abc"
        self.assertEqual(credito_aviso_sla_horas("emp1"), 24)
