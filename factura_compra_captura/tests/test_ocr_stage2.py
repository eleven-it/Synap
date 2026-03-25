"""Stage 2: clasificación + cabecera con confianza/evidencia (aditivo sobre Stage 1)."""

from __future__ import annotations

import os
import tempfile

from django.test import SimpleTestCase
from reportlab.pdfgen import canvas

from factura_compra_captura.ocr.heuristic_pdf import parsear_texto_factura
from factura_compra_captura.services.document_classifier import clasificar_documento
from factura_compra_captura.services.header_parser import parsear_cabecera_documento


TEXTO_FACTURA_SIMPLE = """
PROVEEDOR DEMO SRL
CUIT: 30-70185500-8
Factura A  Fecha de emisión: 15/03/2026
Comp. Nro 0001-00001234
Importe Total: $ 12.345,67
CAE 12345678901234
"""


class DocumentClassifierTests(SimpleTestCase):
    def test_factura_probable_con_keywords(self):
        r = clasificar_documento(TEXTO_FACTURA_SIMPLE, None)
        self.assertEqual(r["tipo_documento"], "invoice_probable")
        self.assertGreaterEqual(r["confidence"], 0.3)
        self.assertIn("detalle", r)

    def test_texto_arbitrario_unknown(self):
        r = clasificar_documento("hola mundo foo bar", None)
        self.assertEqual(r["tipo_documento"], "unknown")
        self.assertLessEqual(r["confidence"], 0.6)

    def test_classifier_usa_estructurado_si_texto_plano_corto(self):
        ocr = {
            "palabras_muestra": [{"text": "FACTURA", "page": 1, "left": 0, "top": 0, "width": 1, "height": 1}],
            "pages": [
                {
                    "page_num": 1,
                    "lines": [{"text": "CAE 123", "line_id": "0-0-0"}],
                }
            ],
        }
        r = clasificar_documento("x", ocr)
        self.assertEqual(r["tipo_documento"], "invoice_probable")


class HeaderParserTests(SimpleTestCase):
    def _assert_modelo_campo(self, campo: dict) -> None:
        self.assertIn("valor", campo)
        self.assertIn("confidence", campo)
        self.assertIn("banda", campo)
        self.assertIn("source", campo)
        self.assertIn("evidencia", campo)
        ev = campo["evidencia"]
        self.assertIn("schema_version", ev)
        self.assertIn("page", ev)
        self.assertIn("bbox", ev)
        self.assertIn("raw_text", ev)

    def test_parseo_desde_heuristica_sin_estructurado(self):
        cab, _, _ = parsear_texto_factura(TEXTO_FACTURA_SIMPLE)
        h = parsear_cabecera_documento(TEXTO_FACTURA_SIMPLE, None, cab)
        for clave in (
            "proveedor",
            "tipo_factura",
            "punto_venta",
            "numero",
            "fecha",
            "total",
        ):
            self._assert_modelo_campo(h[clave])
        self.assertEqual(h["tipo_factura"]["valor"], "FA")
        self.assertEqual(h["punto_venta"]["valor"], "0001")
        self.assertEqual(h["numero"]["valor"], "00001234")
        self.assertIn(h["proveedor"]["source"], ("heuristic", "raw", "structured"))

    def test_estructurado_prioriza_lineas_ocr(self):
        cab, _, _ = parsear_texto_factura(TEXTO_FACTURA_SIMPLE)
        ocr = {
            "pages": [
                {
                    "page_num": 2,
                    "lines": [
                        {
                            "text": "Importe Total: $ 99,50",
                            "line_id": "1-0-1",
                        }
                    ],
                }
            ],
            "palabras_muestra": [],
        }
        h = parsear_cabecera_documento(TEXTO_FACTURA_SIMPLE, ocr, cab)
        self.assertEqual(h["total"]["source"], "structured")
        self.assertEqual(h["total"]["evidencia"]["page"], 2)


class Stage2IntegrationTests(SimpleTestCase):
    def test_analizar_pdf_incluye_classification_y_header_en_document_engine_v1(self):
        from factura_compra_captura.ocr.heuristic_pdf import analizar_archivo_factura

        texto_pdf = TEXTO_FACTURA_SIMPLE
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name
        try:
            c = canvas.Canvas(path, pagesize=(400, 200))
            for i, line in enumerate(texto_pdf.strip().split("\n")):
                c.drawString(40, 160 - i * 14, line.strip()[:80])
            c.save()
            out = analizar_archivo_factura(path, "application/pdf")
        finally:
            os.unlink(path)
        de = out["raw"].get("document_engine_v1")
        self.assertIsNotNone(de)
        self.assertGreaterEqual(de.get("version"), 5)
        self.assertIn("document_score", de)
        self.assertGreaterEqual(float(de["document_score"]), 0.0)
        self.assertIn("classification", de)
        self.assertIn("parsed", de)
        self.assertIn("header", de["parsed"])
        self.assertIn("header_quality", de["parsed"])
        self.assertIn("line_items", de["parsed"])
        self.assertIn("line_items_quality", de)
        self.assertIn("validations", de)
        self.assertIn("validation_summary", de)
        hq = de["parsed"]["header_quality"]
        self.assertIn("campos_criticos", hq)
        self.assertIn("consistencia_legacy", hq)
        self.assertEqual(de["classification"]["tipo_documento"], "invoice_probable")
