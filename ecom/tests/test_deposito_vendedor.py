"""Tests resolución depósito del vendedor (fail-closed)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ecom.services.deposito_vendedor import (
    DepositoVendedorNoResuelto,
    resolver_id_deposito_vendedor,
)


class TestResolverIdDepositoVendedor(SimpleTestCase):
    def test_prioriza_user_id_deposito(self):
        dep = resolver_id_deposito_vendedor(
            session={"user": {"id_usuario": 28, "id_deposito": 6, "base_empresa": "administranet"}},
            consultar_mysql=False,
        )
        self.assertEqual(dep, 6)

    def test_body_no_pisa_vendedor(self):
        dep = resolver_id_deposito_vendedor(
            session={"user": {"id_deposito": 6}},
            data={"id_deposito": 1},
            permitir_body=True,
            priorizar_vendedor=True,
            consultar_mysql=False,
        )
        self.assertEqual(dep, 6)

    def test_sin_datos_falla(self):
        with self.assertRaises(DepositoVendedorNoResuelto):
            resolver_id_deposito_vendedor(
                session={"user": {"id_usuario": 28}},
                consultar_mysql=False,
            )

    @patch("ecom.services.deposito_vendedor.fetch_id_deposito_usuario", return_value=6)
    def test_fallback_mysql_usuarios(self, _mock):
        dep = resolver_id_deposito_vendedor(
            session={"user": {"id_usuario": 28, "base_empresa": "administranet"}},
            data={"id_deposito": 1},
            consultar_mysql=True,
        )
        self.assertEqual(dep, 6)

    def test_no_acepta_cero(self):
        with self.assertRaises(DepositoVendedorNoResuelto):
            resolver_id_deposito_vendedor(
                session={"user": {"id_deposito": 0}},
                consultar_mysql=False,
            )
