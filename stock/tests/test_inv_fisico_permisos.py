# -*- coding: utf-8 -*-
"""Tests permisos inventario físico (Fase 1)."""
from django.test import SimpleTestCase

from core.constantes_permisos import PERMISOS_POR_MODULO
from core.services.synap_permisos_seed import _filas_catalogo


class InvFisicoPermisosTests(SimpleTestCase):
    """Catálogo Synap incluye permisos stock.inventario_fisico.*."""

    PERMISOS_ESPERADOS = {
        "stock.inventario_fisico.contar": "Conteo móvil de inventario físico",
        "stock.inventario_fisico.gestionar": "Gestionar campañas de inventario físico",
        "stock.inventario_fisico.autorizar": "Autorizar y aplicar ajustes de inventario físico",
    }

    def test_permisos_en_modulo_stock(self):
        stock_dict = dict(PERMISOS_POR_MODULO["Stock"])
        for key, label in self.PERMISOS_ESPERADOS.items():
            self.assertIn(key, stock_dict)
            self.assertEqual(stock_dict[key], label)

    def test_permisos_en_seed_synap(self):
        filas = _filas_catalogo()
        keys_seed = {f[0] for f in filas}
        for key in self.PERMISOS_ESPERADOS:
            self.assertIn(key, keys_seed)
