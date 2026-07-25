# -*- coding: utf-8 -*-
"""Tests permisos workflow crédito pedidos (Fase 0)."""
from unittest.mock import patch

from django.test import SimpleTestCase

from core.constantes_permisos import PERMISOS_POR_MODULO
from core.services.administranet_permisos_usuario import tiene_permiso_administranet
from core.services.synap_permisos_seed import _filas_catalogo
from ecom.permissions import puede_aprobar_credito, puede_configurar_credito


class CreditoPedidosPermisosCatalogoTests(SimpleTestCase):
    PERMISOS_ESPERADOS = {
        "finance.credito.aprobar": "Aprobar crédito en cola Finanzas",
        "finance.credito.configurar": "Configurar políticas y plantillas de crédito",
    }

    def test_permisos_en_modulo_finance(self):
        finance_dict = dict(PERMISOS_POR_MODULO["Finance"])
        for key, label in self.PERMISOS_ESPERADOS.items():
            self.assertIn(key, finance_dict)
            self.assertEqual(finance_dict[key], label)

    def test_permisos_en_seed_synap(self):
        keys_seed = {f[0] for f in _filas_catalogo()}
        for key in self.PERMISOS_ESPERADOS:
            self.assertIn(key, keys_seed)


class CreditoPedidosPermisosRuntimeTests(SimpleTestCase):
    def test_finance_wildcard_otorga_aprobar_y_configurar(self):
        sess = {"synap_permisos": ["finance.*"]}
        self.assertTrue(puede_aprobar_credito(sess))
        self.assertTrue(puede_configurar_credito(sess))

    def test_wildcard_total_otorga_ambos(self):
        sess = {"synap_permisos": ["*"]}
        self.assertTrue(puede_aprobar_credito(sess))
        self.assertTrue(puede_configurar_credito(sess))

    def test_ecom_pedidos_aprobar_no_otorga_credito(self):
        sess = {"synap_permisos": ["ecom.pedidos.aprobar"]}
        self.assertFalse(puede_aprobar_credito(sess))
        self.assertFalse(puede_configurar_credito(sess))

    def test_segregacion_aprobar_sin_configurar(self):
        sess = {"synap_permisos": ["finance.credito.aprobar"]}
        self.assertTrue(puede_aprobar_credito(sess))
        self.assertFalse(puede_configurar_credito(sess))

    def test_segregacion_configurar_sin_aprobar(self):
        sess = {"synap_permisos": ["finance.credito.configurar"]}
        self.assertFalse(puede_aprobar_credito(sess))
        self.assertTrue(puede_configurar_credito(sess))

    @patch("core.services.administranet_permisos_usuario.get_permisos_totales_administranet")
    def test_tiene_permiso_administranet_finance_credito_aprobar(self, mock_get):
        mock_get.return_value = {"finance.credito.aprobar"}
        self.assertTrue(
            tiene_permiso_administranet("emp1", 5, "finance.credito.aprobar")
        )
        self.assertFalse(
            tiene_permiso_administranet("emp1", 5, "finance.credito.configurar")
        )

    @patch("core.services.administranet_permisos_usuario.get_permisos_totales_administranet")
    def test_tiene_permiso_administranet_comercial_no_credito(self, mock_get):
        mock_get.return_value = {"ecom.pedidos.aprobar"}
        self.assertFalse(
            tiene_permiso_administranet("emp1", 5, "finance.credito.aprobar")
        )
