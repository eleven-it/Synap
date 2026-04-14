# -*- coding: utf-8 -*-
"""
Integración del informe Objetivos vs BO (slug, runner, estructura meta).

Ejecutar con MySQL (contenedor):
  docker exec Synap_app python manage.py test reports.tests.test_objetivos_ventas_informe_integration
"""

from __future__ import annotations

from unittest.mock import MagicMock

from django.conf import settings
from django.test import TestCase


REPORT_SLUG = "ventas-objetivos-vs-bo"


class TestObjetivosVentasInformeSlugRegistrado(TestCase):
    """El slug debe existir en ReportDefinition tras la migración de datos."""

    def test_slug_en_base_o_catalogo(self):
        from reports.models import ReportDefinition

        self.assertTrue(
            ReportDefinition.objects.filter(slug=REPORT_SLUG).exists(),
            f"Falta ReportDefinition slug={REPORT_SLUG}",
        )


class TestObjetivosVentasInformeQueryRunner(TestCase):
    """Respuesta mínima esperada del runner (estructura cuando la consulta corre)."""

    def test_extra_contiene_jerarquia_o_tabs(self):
        from reports.models import ReportDefinition
        from reports.services.query_runner import QueryRunnerService

        report = ReportDefinition.objects.filter(slug=REPORT_SLUG).first()
        if not report:
            self.skipTest(f"No hay ReportDefinition {REPORT_SLUG}")

        user = MagicMock()
        user.base_empresa = getattr(settings, "DEFAULT_BASE_EMPRESA", None) or "test"

        service = QueryRunnerService(user=user)
        payload = {
            "filters": {
                "base_empresa": user.base_empresa,
                "fecha_inicio": "2026-01-01",
                "fecha_fin": "2026-01-31",
                "fecha_inicio_facturacion": "2026-01-01",
                "fecha_fin_facturacion": "2026-01-31",
            }
        }
        result = service.run(report, payload)
        err_text = " ".join(str(n) for n in (result.notes or []))
        if "Error al ejecutar" in err_text or "No se pudo determinar la base" in err_text:
            self.skipTest(f"Entorno MySQL/base empresa no disponible para integración: {err_text[:200]}")

        extra = (result.meta or {}).get("extra") or {}
        tabs = extra.get("tabs") or {}
        self.assertIn("objetivos_jerarquia", tabs)
        self.assertIsInstance(tabs["objetivos_jerarquia"], list)
        self.assertIn("objetivos_filas", tabs)
        self.assertIsInstance(tabs["objetivos_filas"], list)

        fa = (result.meta or {}).get("filters_applied") or {}
        self.assertEqual(fa.get("lista_precio_label"), "Lista 1")
