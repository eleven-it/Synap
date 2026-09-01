"""Orchestrator: orden CI→PD→ES→VD→FV, lock y vacío sin artefacto."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from mtrix.extractors.base import ExportConfig
from mtrix.models import MtrixArtifact, MtrixConfig, MtrixJob
from mtrix.services.csv_serializer import TIPOS_ORDEN
from mtrix.services.orchestrator import config_to_export, crear_job, ejecutar_job


def _export_cfg(base: str) -> ExportConfig:
    return ExportConfig(
        base_empresa=base,
        fecha_desde="2026-08-01",
        fecha_hasta="2026-08-12",
        proveedores=["TODOS"],
        cnpj_fornecedor="30712345678",
        cnpj_distribuidor="20111111112",
        razon_social_fornecedor="TEST",
        fecha_archivo="20260812",
    )


class OrchestratorTests(TestCase):
    def setUp(self):
        self.base = "emp_orq"
        MtrixConfig.objects.create(base_empresa=self.base, cnpj_fornecedor="30712345678")

    def test_orden_tipos(self):
        self.assertEqual(TIPOS_ORDEN, ("CI", "PD", "ES", "VD", "FV"))

    def test_lock_segunda_corrida(self):
        crear_job(base_empresa=self.base, origen=MtrixJob.Origen.UI)
        with self.assertRaises(RuntimeError):
            crear_job(base_empresa=self.base, origen=MtrixJob.Origen.UI)

    @override_settings(MEDIA_ROOT="")
    def test_vacio_no_crea_artefacto_y_orden_de_llamadas(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with override_settings(MEDIA_ROOT=tmp.name):
            job = crear_job(base_empresa=self.base, origen=MtrixJob.Origen.UI, triggered_by="op")
            llamadas = []

            def make_ext(tipo, rows):
                m = MagicMock()

                def fetch(_conn, _cfg, **kwargs):
                    llamadas.append(tipo)
                    return rows

                m.fetch_rows.side_effect = fetch
                return m

            extractors = {
                "CI": make_ext(
                    "CI",
                    [
                        {
                            "CNPJ_CLIENTE": "20111",
                            "RAZAO_SOCIAL": "ACME",
                            "ENDERECO": "NA",
                            "BAIRRO": "NA",
                            "CEP": "0",
                            "CIDADE": "NA",
                            "ESTADO": "NA",
                            "NOME_RESPONSAVEL": "NA",
                            "TELEFONE": "",
                            "ROTA": "RUTA",
                            "TIPO_LOJ": "Tienda",
                            "REPRESENTATIVIDADE": "0,00",
                        }
                    ],
                ),
                "PD": make_ext("PD", []),
                "ES": make_ext("ES", []),
                "VD": make_ext("VD", []),
                "FV": make_ext("FV", []),
            }
            with patch("mtrix.services.orchestrator.EXTRACTORS", extractors), patch(
                "mtrix.services.orchestrator.config_to_export",
                return_value=_export_cfg(self.base),
            ):
                ejecutar_job(job.id)
            job.refresh_from_db()
            self.assertEqual(job.status, MtrixJob.Estado.COMPLETED)
            self.assertEqual(llamadas, ["CI", "PD", "ES", "VD", "FV"])
            tipos = list(MtrixArtifact.objects.filter(job=job).values_list("tipo", flat=True))
            self.assertEqual(tipos, ["CI"])
            dest = Path(tmp.name) / "mtrix" / self.base / str(job.id)
            self.assertTrue(dest.exists())
            self.assertTrue(any(p.suffix == ".csv" for p in dest.iterdir()))
            self.assertEqual(datetime.fromisoformat(str(job.fecha_desde)).strftime("%Y-%m-%d") if False else str(job.fecha_desde), "2026-08-01")

    @override_settings(MEDIA_ROOT="")
    def test_un_archivo_por_tipo_aunque_haya_varios_proveedores(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with override_settings(MEDIA_ROOT=tmp.name):
            job = crear_job(base_empresa=self.base, origen=MtrixJob.Origen.UI, triggered_by="op")
            llamadas = []

            def make_ext(tipo, rows):
                m = MagicMock()

                def fetch(_conn, _cfg, **kwargs):
                    llamadas.append((tipo, kwargs.get("codigos_prov")))
                    return rows

                m.fetch_rows.side_effect = fetch
                return m

            row_pd = {
                "CODIGO_PRODUTO": "A",
                "DESCRICAO": "Art",
                "DIVISAO_MARCA": "M",
                "DIVISAO_RUBRO": "R",
                "EAN": "1",
                "DISCONTINUO": "No",
            }
            extractors = {
                "CI": make_ext("CI", []),
                "PD": make_ext("PD", [row_pd]),
                "ES": make_ext("ES", []),
                "VD": make_ext("VD", []),
                "FV": make_ext("FV", []),
            }
            cfg = _export_cfg(self.base)
            cfg.proveedores = ["23", "29", "31"]
            with patch("mtrix.services.orchestrator.EXTRACTORS", extractors), patch(
                "mtrix.services.orchestrator.config_to_export",
                return_value=cfg,
            ):
                ejecutar_job(job.id)
            job.refresh_from_db()
            self.assertEqual(job.status, MtrixJob.Estado.COMPLETED)
            self.assertEqual(llamadas, [
                ("CI", None),
                ("PD", ["23", "29", "31"]),
                ("ES", ["23", "29", "31"]),
                ("VD", ["23", "29", "31"]),
                ("FV", None),
            ])
            tipos = list(MtrixArtifact.objects.filter(job=job).values_list("tipo", flat=True))
            self.assertEqual(tipos, ["PD"])
            self.assertEqual(MtrixArtifact.objects.filter(job=job, tipo="PD").count(), 1)

    @patch("mtrix.services.orchestrator.obtener_razon_empresa", return_value="SMART")
    @patch("mtrix.services.orchestrator.obtener_cnpj_distribuidor", return_value="30711007462")
    @patch(
        "mtrix.services.orchestrator.resolver_fechas_mysql",
        return_value=("2026-08-22", "2026-08-27"),
    )
    def test_cnpj_sale_del_cuit_empresa_no_del_config(self, mock_fechas, _cnpj, _razon):
        cfg = MtrixConfig.objects.get(base_empresa=self.base)
        cfg.cnpj_fornecedor = "20939802593"
        cfg.fecha_personalizada = True
        cfg.save()
        export = config_to_export(cfg, origen=MtrixJob.Origen.CRON)
        self.assertEqual(export.cnpj_fornecedor, "30711007462")
        self.assertEqual(export.cnpj_distribuidor, "30711007462")
        kwargs = mock_fechas.call_args.kwargs
        self.assertFalse(kwargs["usar_personalizada"])
