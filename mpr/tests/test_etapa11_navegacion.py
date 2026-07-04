"""Etapa 11 — Navegación MPR: tablero consolidado como hub; wizard/ventana pack secundarios."""

import os

from django.test import SimpleTestCase
from django.urls import reverse

from core.utils.utils import APPS_MENU


def _mpr_menu():
    for app in APPS_MENU:
        if app.get("id") == "mpr":
            return app
    return None


def _read_template(*parts):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, *parts)
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestMenuMprEtapa11(SimpleTestCase):
    """Menú lateral: producción diaria primero; wizard demovido."""

    def test_modulo_mpr_entra_por_tablero_produccion(self):
        mpr = _mpr_menu()
        self.assertIsNotNone(mpr)
        self.assertEqual(mpr["url"], "mpr:tablero_produccion")

    def test_seccion_produccion_diaria_con_tablero_y_parte(self):
        mpr = _mpr_menu()
        secciones = {s["seccion"]: s for s in mpr["submenus"]}
        prod = secciones.get("Producción diaria")
        self.assertIsNotNone(prod)
        urls = [it["url"] for it in prod["items"]]
        self.assertEqual(urls[0], "mpr:tablero_produccion")
        self.assertIn("mpr:parte_produccion", urls)
        self.assertIn("mpr:clasificacion_produccion", urls)

    def test_wizard_en_trazabilidad_avanzada(self):
        mpr = _mpr_menu()
        secciones = {s["seccion"]: s for s in mpr["submenus"]}
        traz = secciones.get("Trazabilidad OPT (avanzado)")
        self.assertIsNotNone(traz)
        labels = [it["label"] for it in traz["items"]]
        self.assertIn("Asistente legacy", labels)
        self.assertIn("Crear OPT (demanda pack)", labels)


class TestTemplatesNavegacionEtapa11(SimpleTestCase):
    """Plantillas clave no promueven ventana pack como CTA principal."""

    def test_tablero_produccion_enlace_opt_list(self):
        html = _read_template("templates", "mpr", "tablero_produccion.html")
        self.assertIn("opt_list_url", html)
        self.assertIn("Trazabilidad OPT", html)
        self.assertNotIn("ventana_pack_url", html)

    def test_ventana_pack_banner_legacy_sin_wizard(self):
        html = _read_template("templates", "mpr", "ventana_pack.html")
        self.assertIn("Flujo avanzado de trazabilidad OPT", html)
        self.assertIn("wizard_paso_max", html)
        self.assertNotIn("de 5:", html)

    def test_opt_detail_enlaza_parte_produccion(self):
        html = _read_template("templates", "mpr", "opt_detail.html")
        self.assertIn("mpr:parte_produccion", html)
        self.assertNotIn("paso=3", html)

    def test_crear_opp_url_es_parte_produccion(self):
        from mpr import views

        src = open(views.__file__, encoding="utf-8").read()
        self.assertIn('"crear_opp_url": reverse("mpr:parte_produccion")', src)
        self.assertNotIn('reverse("mpr:wizard") + f"?paso=3', src)

    def test_urls_canonicas_resuelven(self):
        self.assertTrue(reverse("mpr:tablero_produccion").endswith("/tablero-produccion/"))
        self.assertTrue(reverse("mpr:parte_produccion").endswith("/parte-produccion/"))
        self.assertTrue(reverse("mpr:opt_list").endswith("/opt/"))
