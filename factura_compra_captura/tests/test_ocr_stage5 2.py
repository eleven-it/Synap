"""Stage 5: plantillas por proveedor, señales de flujo y feedback de analista (aditivo)."""

from __future__ import annotations

import os
import tempfile

from django.test import SimpleTestCase
from reportlab.pdfgen import canvas

from factura_compra_captura.ocr.heuristic_pdf import (
    _enriquecer_raw_document_engine_stage2,
    analizar_archivo_factura,
)
from factura_compra_captura.services.supplier_template_engine import (
    append_analyst_correction,
    build_template_application,
    build_workflow_signals,
    default_analyst_feedback,
)
from factura_compra_captura.services.supplier_template_matcher import (
    match_supplier_template,
)


class Stage5SupplierTemplateTests(SimpleTestCase):
    """S1, S2, S3, S5 — integración con pipeline heurístico."""

    def test_s1_cuit_conocido_asigna_plantilla(self):
        texto = """
        Factura A
        CUIT: 30-70185500-8
        Comp. Nro 0001-00001234
        Fecha 15/03/2026
        Total $ 100,00
        """
        raw: dict = {}
        cab = {
            "proveedor_cuit_texto": "30-70185500-8",
            "nro_comprobante_texto": "0001-00001234",
        }
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            cab,
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        self.assertGreaterEqual(de.get("version"), 6)
        m = de.get("supplier_template_match") or {}
        self.assertEqual(m.get("template_id"), "demo_cuit_30701855008")
        self.assertEqual(m.get("matched_by"), "cuit_legacy")

    def test_s2_cuit_desconocido_sin_plantilla(self):
        texto = """
        Factura A
        CUIT: 20-12345678-9
        Comp. Nro 0001-00000001
        Total $ 50,00
        """
        raw: dict = {}
        cab = {"proveedor_cuit_texto": "20-12345678-9"}
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            cab,
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        m = de.get("supplier_template_match") or {}
        self.assertIsNone(m.get("template_id"))
        ta = de.get("template_application") or {}
        self.assertFalse(ta.get("active"))

    def test_s3_plantilla_extrae_cae_en_header_fields(self):
        texto = """
        CUIT: 30-70185500-8
        CAE N°: 71234567890123
        Total $ 1,00
        """
        raw: dict = {}
        cab = {"proveedor_cuit_texto": "30-70185500-8"}
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            cab,
            [],
            ocr_structured=None,
            document_engine_v1_base=None,
            engine_mode="legacy",
        )
        de = raw["document_engine_v1"]
        ta = de.get("template_application") or {}
        self.assertTrue(ta.get("active"))
        hf = ta.get("header_fields") or {}
        self.assertEqual(hf.get("cae_numero"), "71234567890123")
        # parsed.header no debe depender del CAE de plantilla (contrato estable)
        ph = (de.get("parsed") or {}).get("header") or {}
        self.assertNotIn("cae_numero", ph)

    def test_s5_workflow_signals_y_keys_documentadas(self):
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
        ws = de.get("workflow_signals") or {}
        self.assertEqual(ws.get("schema_version"), 1)
        self.assertIn("supplier_template_id", ws)
        self.assertIn("template_matched", ws)
        self.assertIn("suggested_review", ws)
        self.assertEqual(ws.get("blocking_issues"), False)
        self.assertEqual(ws.get("supplier_template_id"), "demo_cuit_30701855008")

    def test_analizar_pdf_incluye_stage5_en_document_engine_v1(self):
        texto = """
        Factura
        CUIT: 30-70185500-8
        Comp. Nro 0001-00000001
        Fecha 01/01/2026
        Importe Total: $ 100,00
        Producto test 2 50,00 100,00
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name
        try:
            c = canvas.Canvas(path, pagesize=(400, 320))
            for i, line in enumerate(texto.strip().split("\n")):
                c.drawString(40, 300 - i * 14, line.strip()[:95])
            c.save()
            out = analizar_archivo_factura(path, "application/pdf")
        finally:
            os.unlink(path)
        de = out["raw"].get("document_engine_v1")
        self.assertIsNotNone(de)
        self.assertGreaterEqual(de.get("version"), 6)
        self.assertIn("supplier_template_match", de)
        self.assertIn("template_application", de)
        self.assertIn("workflow_signals", de)
        self.assertIn("analyst_feedback", de)


class Stage5TemplateApplicationUnitTests(SimpleTestCase):
    """S4 — suplemento de líneas sin mutar parsed.line_items."""

    def test_s4_suplemento_cuando_hay_mas_lineas_regex_que_parseadas(self):
        texto = (
            "CUIT: 30-70185500-8\n"
            "LINEAITEMM UNO MAS 1 10,00\n"
            "LINEAITEMM DOS MAS 2 20,00\n"
            "LINEAITEMM TRES MAS 3 30,00\n"
        )
        de = {
            "parsed": {
                "header": {},
                "line_items": [{"item_index": 0, "source": "test"}],
            },
            "validation_summary": {"has_warnings": False, "has_errors": False},
        }
        m = match_supplier_template({"proveedor_cuit_texto": "30-70185500-8"}, {})
        ta = build_template_application(texto, de, m)
        self.assertTrue(ta.get("active"))
        sup = ta.get("line_items_supplement") or []
        self.assertEqual(len(sup), 2)
        self.assertEqual(sup[0].get("source"), "template_rule")
        self.assertEqual(len(de["parsed"]["line_items"]), 1)


class Stage5WorkflowSignalsUnitTests(SimpleTestCase):
    def test_suggested_review_cuando_hay_warnings(self):
        de = {
            "supplier_template_match": {"template_id": None},
            "validation_summary": {"has_warnings": True, "has_errors": False},
        }
        ws = build_workflow_signals(de)
        self.assertTrue(ws["suggested_review"])


class Stage5AnalystFeedbackTests(SimpleTestCase):
    """S6 — captura segura de correcciones."""

    def test_default_y_append(self):
        fb = default_analyst_feedback()
        self.assertEqual(fb.get("schema_version"), 1)
        self.assertEqual(fb.get("corrections"), [])
        fb2 = append_analyst_correction(
            fb, campo="total", valor_anterior="1", valor_nuevo="2"
        )
        self.assertEqual(len(fb2["corrections"]), 1)
        self.assertEqual(fb2["corrections"][0]["campo"], "total")

    def test_append_normaliza_schema_roto(self):
        fb = append_analyst_correction(
            {"schema_version": 99},
            campo="x",
            valor_anterior=None,
            valor_nuevo="y",
        )
        self.assertEqual(fb["schema_version"], 1)
        self.assertEqual(len(fb["corrections"]), 1)
