"""Tests de modelos Mtrix (unique config y lock de job activo)."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from mtrix.models import MtrixConfig, MtrixJob
from mtrix.services.orchestrator import crear_job


class MtrixModelsTests(TestCase):
    def test_config_unique_base_empresa(self):
        MtrixConfig.objects.create(base_empresa="emp_a")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MtrixConfig.objects.create(base_empresa="emp_a")

    def test_un_solo_job_queued_o_running_por_empresa(self):
        MtrixJob.objects.create(
            base_empresa="emp_a",
            status=MtrixJob.Estado.RUNNING,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MtrixJob.objects.create(
                    base_empresa="emp_a",
                    status=MtrixJob.Estado.QUEUED,
                )

    def test_job_completado_no_bloquea_otro(self):
        MtrixJob.objects.create(
            base_empresa="emp_a",
            status=MtrixJob.Estado.COMPLETED,
        )
        segundo = MtrixJob.objects.create(
            base_empresa="emp_a",
            status=MtrixJob.Estado.QUEUED,
        )
        self.assertEqual(segundo.status, MtrixJob.Estado.QUEUED)

    def test_crear_job_rechaza_si_hay_activo(self):
        crear_job(base_empresa="emp_a", origen=MtrixJob.Origen.UI, triggered_by="op")
        with self.assertRaises(RuntimeError):
            crear_job(base_empresa="emp_a", origen=MtrixJob.Origen.UI)

    def test_sftp_enviar_automatico_default_no(self):
        cfg = MtrixConfig.objects.create(base_empresa="emp_b")
        self.assertFalse(cfg.sftp_enviar_automatico)
        self.assertFalse(cfg.programador_activo)
