# -*- coding: utf-8 -*-
"""Tests cliente BCRA (mock HTTP)."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.bcra_cotizacion import BCRA_VARIABLE_IDS, consultar_bcra, limpiar_cache_bcra


class BcraCotizacionTest(SimpleTestCase):
    def setUp(self):
        limpiar_cache_bcra()

    def tearDown(self):
        limpiar_cache_bcra()

    @patch("core.services.bcra_cotizacion.urlopen")
    def test_consulta_referencia_ok(self, mock_urlopen):
        payload = b'{"status":200,"results":[{"fecha":"2026-08-01","valor":1180.5}]}'
        mock_urlopen.return_value.__enter__.return_value.read.return_value = payload

        res = consultar_bcra("bcra_referencia", fecha=date(2026, 8, 2), timeout_seg=3, usar_cache=False)
        self.assertTrue(res["disponible"])
        self.assertEqual(res["valor"], 1180.5)
        self.assertEqual(res["tipo"], "bcra_referencia")

    @patch("core.services.bcra_cotizacion.urlopen")
    def test_api_caida_fail_soft(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timeout")
        res = consultar_bcra("bcra_referencia", fecha=date(2026, 8, 2), usar_cache=False)
        self.assertFalse(res["disponible"])
        self.assertIsNone(res["valor"])
        self.assertIn("BCRA", res["mensaje"])

    def test_manual_only_sin_consulta(self):
        res = consultar_bcra("manual_only", fecha=date(2026, 8, 2))
        self.assertFalse(res["disponible"])
        self.assertIn("manual", res["mensaje"].lower())

    @patch("core.services.bcra_cotizacion._fetch_variable")
    def test_mid_promedia_compra_venta(self, mock_fetch):
        mock_fetch.side_effect = lambda vid, *_a, **_k: Decimal("100") if vid == BCRA_VARIABLE_IDS["bcra_compra"] else Decimal("200")
        res = consultar_bcra("mid", fecha=date(2026, 8, 2), usar_cache=False)
        self.assertTrue(res["disponible"])
        self.assertEqual(res["valor"], 150.0)
