# -*- coding: utf-8 -*-
"""Tests rutas esqueleto inventario físico (Fase 1)."""
import re
from pathlib import Path

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

    def test_api_conteo_registrados_url(self):
        self.assertEqual(reverse("stock:api_conteo_registrados"), "/stock/api/conteo/registrados/")

    def test_api_campana_autorizar_url(self):
        self.assertEqual(
            reverse("stock:api_campana_autorizar", kwargs={"id_campana": 7}),
            "/stock/api/campana/7/autorizar/",
        )

    def test_api_campana_ajuste_recalcular_url(self):
        self.assertEqual(
            reverse("stock:api_campana_ajuste_recalcular", kwargs={"id_campana": 7}),
            "/stock/api/campana/7/ajuste/recalcular/",
        )

    def test_api_campana_linea_ajuste_url(self):
        self.assertEqual(
            reverse("stock:api_campana_linea_ajuste", kwargs={"id_campana": 7, "id_linea": 9}),
            "/stock/api/campana/7/linea/9/ajuste/",
        )

    def test_api_campana_linea_movimientos_url(self):
        self.assertEqual(
            reverse("stock:api_campana_linea_movimientos", kwargs={"id_campana": 7, "id_linea": 9}),
            "/stock/api/campana/7/linea/9/movimientos/",
        )

    def test_api_campana_marcar_no_contados_cero_url(self):
        self.assertEqual(
            reverse(
                "stock:api_campana_marcar_no_contados_cero",
                kwargs={"id_campana": 7},
            ),
            "/stock/api/campana/7/marcar-no-contados-cero/",
        )

    def test_inventario_fisico_analizador_url(self):
        self.assertEqual(
            reverse("stock:inventario_fisico_analizador", kwargs={"id_campana": 3}),
            "/stock/inventario-fisico/3/analizador/",
        )

    def test_inventario_fisico_export_xlsx_url(self):
        self.assertEqual(
            reverse("stock:inventario_fisico_export_xlsx", kwargs={"id_campana": 3}),
            "/stock/inventario-fisico/3/exportar/",
        )

    def test_inventario_fisico_linea_url(self):
        self.assertEqual(
            reverse("stock:inventario_fisico_linea", kwargs={"id_campana": 3, "id_linea": 9}),
            "/stock/inventario-fisico/3/linea/9/",
        )


class AnalizadorPlantillaSinDialogosNativosTest(SimpleTestCase):
    """El analizador usa modales Synap, no alert/confirm/prompt del navegador."""

    _PATRONES_PROHIBIDOS = (
        re.compile(r"\balert\s*\("),
        re.compile(r"\bconfirm\s*\("),
        re.compile(r"\bprompt\s*\("),
        re.compile(r"\bwindow\.alert\s*\("),
        re.compile(r"\bwindow\.confirm\s*\("),
        re.compile(r"\bwindow\.prompt\s*\("),
    )

    def test_analizador_html_sin_dialogos_nativos(self):
        ruta = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "stock"
            / "inventario_fisico"
            / "analizador.html"
        )
        contenido = ruta.read_text(encoding="utf-8")
        for patron in self._PATRONES_PROHIBIDOS:
            self.assertIsNone(
                patron.search(contenido),
                f"Se encontró diálogo nativo prohibido: {patron.pattern}",
            )
        self.assertIn("confirmOpen", contenido)
        self.assertIn("Diferencia real", contenido)
