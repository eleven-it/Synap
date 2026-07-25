# -*- coding: utf-8 -*-
"""Desacople crédito vs aprobación comercial (REQ-APR-02, Fase B)."""

import unittest
from decimal import Decimal
from unittest.mock import patch

from ecom.services.aprobacion_pedidos import evaluar_reglas


class _FakeCart:
    def __init__(self, total="100"):
        self.total = Decimal(total)
        self.descuento_pie_pct = Decimal("0")
        self.idcliente = 10
        self.items = []


class TestCreditoDesacopleComercial(unittest.TestCase):
    @patch("ecom.services.aprobacion_pedidos.umbrales_aprobacion_pedidos")
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.aprobacion_pedidos.credito_pedidos_activo", return_value=True)
    def test_flag_credito_on_no_dispara_regla_comercial(
        self, _credito_on, _aprob_on, mock_umbral
    ):
        mock_umbral.return_value = {"monto": None, "desc_pie": None, "desc_renglon": None}
        cart = _FakeCart()
        req, reglas = evaluar_reglas(
            "emp1", cart, {}, autorizacion_sistema="No Autorizado"
        )
        self.assertFalse(req)
        self.assertNotIn("credito_no_autorizado", reglas)

    @patch("ecom.services.aprobacion_pedidos.umbrales_aprobacion_pedidos")
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.aprobacion_pedidos.credito_pedidos_activo", return_value=False)
    def test_flag_credito_off_mantiene_regla_legacy(
        self, _credito_off, _aprob_on, mock_umbral
    ):
        mock_umbral.return_value = {"monto": None, "desc_pie": None, "desc_renglon": None}
        cart = _FakeCart()
        req, reglas = evaluar_reglas(
            "emp1", cart, {}, autorizacion_sistema="No Autorizado"
        )
        self.assertTrue(req)
        self.assertIn("credito_no_autorizado", reglas)

    @patch("ecom.services.aprobacion_pedidos.umbrales_aprobacion_pedidos")
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.aprobacion_pedidos.credito_pedidos_activo", return_value=True)
    def test_monto_sigue_disparando_con_credito_on(
        self, _credito_on, _aprob_on, mock_umbral
    ):
        mock_umbral.return_value = {
            "monto": Decimal("50"),
            "desc_pie": None,
            "desc_renglon": None,
        }
        cart = _FakeCart(total="200")
        req, reglas = evaluar_reglas(
            "emp1", cart, {}, autorizacion_sistema="No Autorizado"
        )
        self.assertTrue(req)
        self.assertIn("monto", reglas)
        self.assertNotIn("credito_no_autorizado", reglas)
