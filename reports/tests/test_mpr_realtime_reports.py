# Tests TDD para reportes MPR en tiempo real (QueryRunnerService). Especificaciones en docs/reports/mpr/ESPEC_MPR_*.md

from unittest.mock import MagicMock, patch

from django.test import TestCase

from reports.models import ReportDefinition
from reports.services.query_runner import QueryResult, QueryRunnerService


def _reporte_fake(slug: str, name: str = "Reporte MPR"):
    """ReportDefinition fake para tests (sin guardar en DB)."""
    report = MagicMock(spec=ReportDefinition)
    report.slug = slug
    report.name = name
    report.category = "operational"
    report.version = "1.0.0"
    report.config = {}
    return report


class TestMprOptAtrasadasRunner(TestCase):
    """ESPEC_MPR_OPT_ATRASADAS: slug mpr-opt-atrasadas."""

    def test_sin_base_empresa_retorna_data_vacia_y_notes(self):
        report = _reporte_fake("mpr-opt-atrasadas", "OPT atrasadas")
        payload = {"filters": {}}
        user = MagicMock()
        with patch("reports.services.query_runner.settings") as mock_settings:
            mock_settings.DEFAULT_BASE_EMPRESA = None
            runner = QueryRunnerService(user)
            result = runner.run(report, payload)
        self.assertIsInstance(result, QueryResult)
        self.assertEqual(result.data, [])
        self.assertIn("total_opt_atrasadas", result.totals)
        self.assertEqual(result.totals["total_opt_atrasadas"], 0)
        self.assertTrue(any("base_empresa" in n.lower() or "empresa" in n.lower() for n in result.notes))

    def test_con_base_empresa_y_mock_retorna_data_y_totals(self):
        report = _reporte_fake("mpr-opt-atrasadas", "OPT atrasadas")
        payload = {"filters": {"base_empresa": "empresa92"}}
        user = MagicMock()
        filas_mock = [
            {"id_lista_produccion": 1, "codigo_articulo": "ART1", "cantidad_pendiente_prod": 10},
            {"id_lista_produccion": 2, "codigo_articulo": "ART2", "cantidad_pendiente_prod": 5},
        ]
        with patch("mpr.services.listar_opt_listado", return_value=filas_mock):
            runner = QueryRunnerService(user)
            result = runner.run(report, payload)
        self.assertIsInstance(result, QueryResult)
        self.assertEqual(len(result.data), 2)
        self.assertEqual(result.totals.get("total_opt_atrasadas"), 2)
        self.assertEqual(result.meta["slug"], "mpr-opt-atrasadas")

    def test_meta_slug_es_mpr_opt_atrasadas(self):
        report = _reporte_fake("mpr-opt-atrasadas")
        payload = {"filters": {"base_empresa": "empresa92"}}
        with patch("mpr.services.listar_opt_listado", return_value=[]):
            result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(result.meta["slug"], "mpr-opt-atrasadas")


class TestMprPedidosEstadoRunner(TestCase):
    """ESPEC_MPR_PEDIDOS_ESTADO: slug mpr-pedidos-estado."""

    def test_sin_base_empresa_retorna_data_vacia(self):
        report = _reporte_fake("mpr-pedidos-estado")
        payload = {"filters": {}}
        with patch("reports.services.query_runner.settings") as mock_settings:
            mock_settings.DEFAULT_BASE_EMPRESA = None
            result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(result.data, [])
        self.assertEqual(result.totals.get("total_pedidos", 0), 0)

    def test_con_base_empresa_y_mock_retorna_cuatro_estados(self):
        report = _reporte_fake("mpr-pedidos-estado")
        payload = {"filters": {"base_empresa": "empresa92"}}
        filas_mock = [
            {"estado": "Pendiente", "cantidad": 5},
            {"estado": "Produccion", "cantidad": 3},
            {"estado": "Parcial", "cantidad": 1},
            {"estado": "Terminado", "cantidad": 10},
        ]
        with patch("mpr.services.reporte_mpr_pedidos_por_estado", return_value=filas_mock):
            result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(len(result.data), 4)
        self.assertEqual(result.totals.get("total_pedidos"), 19)
        self.assertEqual(result.meta["slug"], "mpr-pedidos-estado")


class TestMprBrechaDemandaRunner(TestCase):
    """ESPEC_MPR_BRECHA_DEMANDA: slug mpr-brecha-demanda."""

    def test_sin_base_empresa_retorna_data_vacia(self):
        report = _reporte_fake("mpr-brecha-demanda")
        payload = {"filters": {}}
        result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(result.data, [])
        self.assertEqual(result.meta["slug"], "mpr-brecha-demanda")

    def test_con_base_empresa_y_mock_retorna_estructura_esperada(self):
        report = _reporte_fake("mpr-brecha-demanda")
        payload = {"filters": {"base_empresa": "empresa92"}}
        filas_mock = [
            {
                "codigo_articulo": "ART1",
                "descripcion_articulo": "Artículo 1",
                "demanda_pendiente": 100,
                "stock_terminado": 30,
                "cantidad_a_fabricar": 70,
                "urgente": 1,
            },
        ]
        with patch("mpr.services.reporte_mpr_brecha_demanda", return_value=filas_mock):
            result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0]["codigo_articulo"], "ART1")
        self.assertEqual(result.data[0]["cantidad_a_fabricar"], 70)
        self.assertEqual(result.meta["slug"], "mpr-brecha-demanda")


class TestMprMovimientosProduccionRunner(TestCase):
    """ESPEC_MPR_MOVIMIENTOS_PRODUCCION: slug mpr-movimientos-produccion."""

    def test_sin_base_empresa_retorna_data_vacia(self):
        report = _reporte_fake("mpr-movimientos-produccion")
        payload = {"filters": {}}
        with patch("reports.services.query_runner.settings.DEFAULT_BASE_EMPRESA", None):
            result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(result.data, [])
        self.assertEqual(result.totals.get("total_movimientos"), 0)
        self.assertEqual(result.meta["slug"], "mpr-movimientos-produccion")

    def test_con_base_empresa_y_mock_respeta_limit(self):
        report = _reporte_fake("mpr-movimientos-produccion")
        payload = {"filters": {"base_empresa": "empresa92", "limit": 50}}
        filas_mock = [
            {"fecha": "2025-03-01", "tipo_mov": "OPT", "codigo_movimiento": 100, "nro_comprobante": "1", "detalle": "Det"},
        ] * 10
        with patch("mpr.services.reporte_mpr_movimientos", return_value=filas_mock):
            result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(len(result.data), 10)
        self.assertEqual(result.totals.get("total_movimientos"), 10)
        self.assertLessEqual(len(result.data), 200)
        self.assertEqual(result.meta["slug"], "mpr-movimientos-produccion")
