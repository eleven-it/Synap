"""Filtros GET de migración BEST: persistencia de checkboxes destildados."""

from django.test import RequestFactory, SimpleTestCase

from mpr.best_migration.views import (
    _filtro_necesarios_pendientes,
    _tiene_filtros_get,
)


class FiltrosGetMigracionBestTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_sin_query_es_primera_visita(self):
        request = self.rf.get("/mpr/migracion-best/articulos/")
        self.assertFalse(_tiene_filtros_get(request))
        self.assertTrue(_filtro_necesarios_pendientes(request))

    def test_form_submit_sin_necesarios_no_reactiva_cola(self):
        """Destildar «Solo necesarios…» manda estado=/q=/filtrado=1 sin necesarios."""
        request = self.rf.get(
            "/mpr/migracion-best/articulos/",
            {"filtrado": "1", "estado": "", "q": ""},
        )
        self.assertTrue(_tiene_filtros_get(request))
        self.assertFalse(_filtro_necesarios_pendientes(request))

    def test_estado_y_q_vacios_sin_filtrado_tambien_cuentan(self):
        """Regresión: ?estado=&q= no debe tratarse como sin filtros."""
        request = self.rf.get(
            "/mpr/migracion-best/articulos/",
            {"estado": "", "q": ""},
        )
        self.assertTrue(_tiene_filtros_get(request))
        self.assertFalse(_filtro_necesarios_pendientes(request))

    def test_necesarios_explicito_activa_cola(self):
        request = self.rf.get(
            "/mpr/migracion-best/articulos/",
            {"filtrado": "1", "necesarios": "1"},
        )
        self.assertTrue(_filtro_necesarios_pendientes(request))

    def test_todos_desactiva_cola(self):
        request = self.rf.get(
            "/mpr/migracion-best/articulos/",
            {"filtrado": "1", "todos": "1"},
        )
        self.assertFalse(_filtro_necesarios_pendientes(request))

    def test_solo_incluir_stock_cuenta_como_filtro(self):
        request = self.rf.get(
            "/mpr/migracion-best/articulos/",
            {"incluir_stock": "1"},
        )
        self.assertTrue(_tiene_filtros_get(request))
        self.assertFalse(_filtro_necesarios_pendientes(request))
        self.assertEqual(request.GET.get("incluir_stock"), "1")
