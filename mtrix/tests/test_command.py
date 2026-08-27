"""Comando generar_mtrix."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from mtrix.models import MtrixConfig, MtrixJob
from mtrix.services.orchestrator import crear_job


class GenerarMtrixCommandTests(TestCase):
    def test_sin_argumentos_falla(self):
        with self.assertRaises(CommandError):
            call_command("generar_mtrix")

    def test_scheduled_sin_ventana_no_crea(self):
        MtrixConfig.objects.create(base_empresa="emp_cmd", programador_activo=False)
        out = StringIO()
        call_command("generar_mtrix", "--scheduled", stdout=out)
        self.assertIn("Sin jobs programados", out.getvalue())
        self.assertFalse(MtrixJob.objects.exists())

    @patch("mtrix.management.commands.generar_mtrix.ejecutar_job")
    def test_job_id_ejecuta(self, mock_ejecutar):
        job = crear_job(base_empresa="emp_cmd2", origen=MtrixJob.Origen.UI)
        mock_ejecutar.side_effect = lambda pk: MtrixJob.objects.filter(pk=pk).update(
            status=MtrixJob.Estado.COMPLETED
        ) or MtrixJob.objects.get(pk=pk)
        call_command("generar_mtrix", f"--job-id={job.id}")
        mock_ejecutar.assert_called_once_with(job.id)
