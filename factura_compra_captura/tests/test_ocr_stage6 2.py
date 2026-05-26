"""Stage 6: observabilidad, métricas y analítica aditiva sobre document_engine_v1."""

from __future__ import annotations

from django.test import SimpleTestCase

from factura_compra_captura.ocr.heuristic_pdf import _enriquecer_raw_document_engine_stage2
from factura_compra_captura.services.document_engine_analytics import (
    aggregate_correction_analytics,
    build_analytics_snapshot,
    build_document_engine_metrics,
    build_observability_context,
    build_workflow_facing_summary,
)
from factura_compra_captura.services.supplier_template_engine import (
    append_analyst_correction,
    default_analyst_feedback,
)


class Stage6MetricsAndSnapshotTests(SimpleTestCase):
    def test_t2_template_match_metrics_presence(self):
        texto = """
        CUIT: 30-70185500-8
        CAE N°: 12345
        Total $ 10,00
        ITEM UNO LARGO 1 5,00
        """
        raw: dict = {}
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            {"proveedor_cuit_texto": "30-70185500-8"},
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        self.assertGreaterEqual(de.get("version"), 7)
        m = de.get("document_engine_metrics") or {}
        self.assertEqual(m.get("schema_version"), 1)
        tp = m.get("template_performance") or {}
        self.assertTrue(tp.get("matched"))
        self.assertEqual(tp.get("template_id"), "demo_cuit_30701855008")
        self.assertGreaterEqual(tp.get("header_fields_extracted_count", 0), 1)

    def test_t1_workflow_signals_exposure_unchanged_shape(self):
        texto = "CUIT: 20-99999999-9\nTotal $ 1,00\n"
        raw: dict = {}
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            {"proveedor_cuit_texto": "20-99999999-9"},
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        ws = de.get("workflow_signals") or {}
        self.assertEqual(ws.get("schema_version"), 1)
        self.assertIn("suggested_review", ws)
        self.assertEqual(ws.get("blocking_issues"), False)

    def test_t3_corrections_aggregation(self):
        fb = default_analyst_feedback()
        fb = append_analyst_correction(fb, campo="total", valor_anterior="1", valor_nuevo="2")
        fb = append_analyst_correction(fb, campo="total", valor_anterior="2", valor_nuevo="3")
        fb = append_analyst_correction(fb, campo="fecha", valor_anterior=None, valor_nuevo="x")
        agg = aggregate_correction_analytics(fb)
        self.assertEqual(agg.get("schema_version"), 1)
        self.assertEqual(agg.get("corrections_total"), 3)
        self.assertEqual(agg.get("by_field", {}).get("total"), 2)
        self.assertEqual(agg.get("fields_distinct"), 2)

    def test_t4_analytics_snapshot_generation(self):
        texto = "CUIT: 30-70185500-8\nTotal $ 1,00\n"
        raw: dict = {}
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            {"proveedor_cuit_texto": "30-70185500-8"},
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        snap = de.get("analytics_snapshot") or {}
        self.assertEqual(snap.get("schema_version"), 1)
        self.assertIn("captured_at_utc", snap)
        self.assertGreaterEqual(snap.get("document_engine_version", 0), 7)
        self.assertIn("workflow_signals_digest", snap)

    def test_t5_backward_compatibility_keys(self):
        texto = "Factura\nCUIT: 30-70185500-8\nComp. Nro 0001-00000001\nTotal $ 100,00\n"
        raw: dict = {}
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            {
                "proveedor_cuit_texto": "30-70185500-8",
                "nro_comprobante_texto": "0001-00000001",
            },
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        for key in (
            "parsed",
            "classification",
            "validations",
            "validation_summary",
            "supplier_template_match",
            "template_application",
            "workflow_signals",
            "analyst_feedback",
        ):
            self.assertIn(key, de)

    def test_t6_observability_log_fields_strings(self):
        texto = "CUIT: 30-70185500-8\nTotal $ 1,00\n"
        raw: dict = {}
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            {"proveedor_cuit_texto": "30-70185500-8"},
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        obs = de.get("observability") or {}
        self.assertEqual(obs.get("schema_version"), 1)
        lf = obs.get("log_fields") or {}
        self.assertTrue(lf)
        for _k, v in lf.items():
            self.assertIsInstance(v, str)


class Stage6UnitHelpersTests(SimpleTestCase):
    def test_build_metrics_from_partial_de(self):
        de = {
            "version": 7,
            "classification": {"tipo_documento": "invoice_probable", "confidence": 0.9},
            "document_score": 0.75,
            "validation_summary": {
                "has_errors": False,
                "has_warnings": True,
                "counts": {"info": 1, "warning": 1, "error": 0},
                "health_score": 0.85,
            },
            "supplier_template_match": {
                "template_id": "demo_cuit_30701855008",
                "confidence": 0.9,
            },
            "template_application": {
                "active": True,
                "header_fields": {"cae_numero": "1"},
                "line_items_supplement": [{"x": 1}],
            },
            "parsed": {"line_items": [1, 2]},
            "line_items_quality": {"item_count": 2},
        }
        m = build_document_engine_metrics(de)
        self.assertEqual(m["template_performance"]["line_supplement_count"], 1)
        self.assertEqual(m["line_items"]["parsed_count"], 2)

    def test_snapshot_is_deterministic_subset(self):
        de = {
            "version": 7,
            "document_engine_metrics": {"schema_version": 1},
            "correction_analytics": {"schema_version": 1, "corrections_total": 0},
            "workflow_facing_summary": {"schema_version": 1, "headline": "x"},
            "workflow_signals": {"template_matched": True, "suggested_review": False},
        }
        s = build_analytics_snapshot(de)
        self.assertEqual(s["document_engine_version"], 7)
        self.assertEqual(s["workflow_signals_digest"]["template_matched"], True)
