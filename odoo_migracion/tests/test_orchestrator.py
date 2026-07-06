"""Tests orquestador con mocks."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from odoo_migracion.models import MigrationJob, OdooConnection
from odoo_migracion.services.migration_orchestrator import run_domain_batch


class OrchestratorTests(TestCase):
    def setUp(self):
        self.conexion = OdooConnection.objects.create(
            nombre="Test",
            base_empresa="administranet_test",
            base_url="https://odoo.test",
            database="odoo",
        )
        self.conexion.set_api_key("fake-key")
        self.conexion.save()

    @patch("odoo_migracion.services.migration_orchestrator.OdooJson2Client")
    @patch("odoo_migracion.extractors.maestros.RubroExtractor.extract")
    @patch("odoo_migracion.extractors.maestros.RubroExtractor.count")
    def test_run_domain_batch_rubro(self, mock_count, mock_extract, mock_client_cls):
        mock_count.return_value = 1
        mock_extract.return_value = [
            {"CodigoRubro": 1, "NombreRubro": "General", "anulado": "No"},
        ]
        mock_client = MagicMock()
        mock_client.create.return_value = 42
        mock_client.search_read.return_value = []
        mock_client_cls.return_value = mock_client

        job = MigrationJob.objects.create(
            conexion=self.conexion,
            dominio="rubro",
            estado=MigrationJob.Estado.EN_CURSO,
            iniciado_at=timezone.now(),
        )
        result = run_domain_batch(
            self.conexion,
            "rubro",
            batch_size=10,
            offset=0,
            job=job,
        )
        self.assertEqual(result.procesados, 1)
        self.assertEqual(result.creados, 1)
        job.refresh_from_db()
        self.assertEqual(job.total_procesados, 1)
