# -*- coding: utf-8 -*-
"""Tests rutas esqueleto inventario físico (Fase 1)."""
from django.test import SimpleTestCase
from django.urls import reverse


class InvFisicoURLTests(SimpleTestCase):
    """Rutas inventario físico resuelven con los paths esperados."""

    def test_inventario_fisico_list_url(self):
        self.assertEqual(reverse("stock:inventario_fisico_list"), "/stock/inventario-fisico/")

    def test_inventario_fisico_crear_url(self):
        self.assertEqual(reverse("stock:inventario_fisico_crear"), "/stock/inventario-fisico/nueva/")

    def test_conteo_mis_url(self):
        self.assertEqual(reverse("stock:conteo_mis"), "/stock/conteo/")

    def test_conteo_campana_url(self):
        self.assertEqual(reverse("stock:conteo_campana", kwargs={"id_campana": 7}), "/stock/conteo/7/")

    def test_api_conteo_prefetch_url(self):
        self.assertEqual(reverse("stock:api_conteo_prefetch"), "/stock/api/conteo/prefetch/")

    def test_api_conteo_sync_url(self):
        self.assertEqual(reverse("stock:api_conteo_sync"), "/stock/api/conteo/sync/")

    def test_api_campana_autorizar_url(self):
        self.assertEqual(
            reverse("stock:api_campana_autorizar", kwargs={"id_campana": 7}),
            "/stock/api/campana/7/autorizar/",
        )

    def test_inventario_fisico_analizador_url(self):
        self.assertEqual(
            reverse("stock:inventario_fisico_analizador", kwargs={"id_campana": 3}),
            "/stock/inventario-fisico/3/analizador/",
        )

    def test_inventario_fisico_linea_url(self):
        self.assertEqual(
            reverse("stock:inventario_fisico_linea", kwargs={"id_campana": 3, "id_linea": 9}),
            "/stock/inventario-fisico/3/linea/9/",
        )
