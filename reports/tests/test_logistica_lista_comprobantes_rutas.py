"""Tests — informe legacy lista comprobantes en rutas."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from reports.models import ReportDefinition
from reports.services.catalog_service import _infer_legacy_section
from reports.services.logistica_lista_comprobantes_rutas import build_listado_sql_and_params
from reports.services.query_runner import QueryResult, QueryRunnerService


class TestLogisticaListaComprobantesRutasCatalogo(SimpleTestCase):
    def test_slug_en_seccion_comprobantes_legacy(self):
        self.assertEqual(
            _infer_legacy_section("comprobantes-rutas"),
            "comprobantes",
        )


class TestLogisticaListaComprobantesRutasQueryRunner(SimpleTestCase):
    def test_cache_ttl_cinco_minutos(self):
        runner = QueryRunnerService(MagicMock())
        ttl = runner._get_cache_ttl("comprobantes-rutas", {})
        self.assertEqual(ttl, 300)

    def test_runner_enruta_a_logistica(self):
        report = MagicMock(spec=ReportDefinition)
        report.slug = "comprobantes-rutas"
        report.name = "Lista comprobantes rutas"
        report.category = "operational"
        report.version = "1.0.0"
        report.config = {}
        payload = {"filters": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31"}}
        user = MagicMock()
        user.base_empresa = None
        fake = QueryResult(
            meta={"slug": "comprobantes-rutas"},
            data=[{"nro_remito": "A", "cod_mov_remito": 1}],
            totals={},
            notes=[],
        )
        with patch.object(
            QueryRunnerService,
            "_run_logistica_lista_comprobantes_rutas",
            return_value=fake,
        ) as mock_run:
            result = QueryRunnerService(user).run(report, payload)
        mock_run.assert_called_once()
        self.assertEqual(result.data[0]["nro_remito"], "A")


class TestBuildListadoSql(SimpleTestCase):
    """Fechas, estado entrega, cliente (uno o varios códigos), chofer."""

    def test_solo_fechas(self):
        filters = {
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
        }
        sql, params = build_listado_sql_and_params(filters, None, False)
        self.assertEqual(params, ["2026-01-01", "2026-01-31"])
        self.assertIn("AS fecha_factura", sql)
        self.assertIn("AS mes_factura_ym", sql)

    def test_filtro_un_cliente(self):
        filters = {
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
            "logistica_id_cliente": "C001",
        }
        sql, params = build_listado_sql_and_params(filters, None, False)
        self.assertIn("cliente.Codigo = %s", sql)
        self.assertEqual(params, ["2026-01-01", "2026-01-31", "C001"])

    def test_filtro_varios_clientes(self):
        filters = {
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
            "logistica_id_cliente": ["A", "B"],
        }
        sql, params = build_listado_sql_and_params(filters, None, False)
        self.assertIn("cliente.Codigo IN (", sql)
        self.assertEqual(params[0:2], ["2026-01-01", "2026-01-31"])
        self.assertEqual(params[2:4], ["A", "B"])

    def test_restriccion_chofer_usa_exists(self):
        filters = {
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
        }
        sql, params = build_listado_sql_and_params(filters, 42, True)
        self.assertIn("EXISTS (", sql)
        self.assertIn("ch_fil.id_usuario = %s", sql)
        self.assertIn("GROUP_CONCAT(DISTINCT ch.nombre_chofer", sql)
        self.assertEqual(params, ["2026-01-01", "2026-01-31", 42])

    def test_filtro_id_ruta(self):
        filters = {
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
            "logistica_id_ruta": 15,
        }
        sql, params = build_listado_sql_and_params(filters, None, False)
        self.assertIn("hoja_ruta.id_ruta = %s", sql)
        self.assertEqual(params, ["2026-01-01", "2026-01-31", 15])

    def test_filtro_chofer_explicito(self):
        filters = {
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-01-31",
            "logistica_aplicar_filtro_chofer_id": True,
            "logistica_id_chofer": 3,
        }
        sql, params = build_listado_sql_and_params(filters, None, False)
        self.assertIn("rc_fc.id_chofer = %s", sql)
        self.assertEqual(params, ["2026-01-01", "2026-01-31", 3])
