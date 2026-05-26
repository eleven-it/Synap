"""Stage 3: ítems de línea en document_engine_v1 (aditivo)."""

from __future__ import annotations

import os
import tempfile

from django.test import SimpleTestCase
from reportlab.pdfgen import canvas

from factura_compra_captura.ocr.heuristic_pdf import parsear_texto_factura
from factura_compra_captura.services.line_items_parser import parsear_line_items_documento


LINEA_ITEM_UNIDADES = (
    "HONORARIOS FEBRERO 2026 1,00 unidades 3154720,97 3154720,970,00 0,00"
)
LINEA_ITEM_SIMPLE = "Producto de prueba 2 150,50 301,00"


class LineItemsParserUnitTests(SimpleTestCase):
    def test_tabla_simple_varias_lineas_ocr(self):
        ocr = {
            "pages": [
                {
                    "page_num": 1,
                    "lines": [
                        {"text": LINEA_ITEM_UNIDADES, "line_id": "0-0-1"},
                        {"text": LINEA_ITEM_UNIDADES, "line_id": "0-0-2"},
                    ],
                }
            ],
            "palabras_muestra": [],
        }
        cab, lineas, _ = parsear_texto_factura("x")
        r = parsear_line_items_documento("", ocr, lineas)
        self.assertEqual(r["quality"]["source"], "structured")
        self.assertFalse(r["quality"]["fallback_used"])
        self.assertGreaterEqual(r["quality"]["item_count"], 2)
        self.assertTrue(r["quality"]["tabular_layout_detected"])
        it0 = r["items"][0]
        self.assertEqual(it0["source"], "structured")
        self.assertIn("schema_version", it0["campos"]["descripcion"]["evidencia"])
        self.assertEqual(it0["campos"]["descripcion"]["evidencia"]["page"], 1)

    def test_un_solo_item(self):
        ocr = {
            "pages": [
                {
                    "page_num": 1,
                    "lines": [{"text": LINEA_ITEM_SIMPLE, "line_id": "0-0-0"}],
                }
            ],
        }
        r = parsear_line_items_documento("", ocr, [])
        self.assertEqual(r["quality"]["item_count"], 1)
        self.assertGreater(r["quality"]["avg_line_confidence"], 0.4)

    def test_multiples_items_alineados_tabular(self):
        ocr = {
            "pages": [
                {
                    "page_num": 1,
                    "lines": [
                        {"text": LINEA_ITEM_SIMPLE, "line_id": "a"},
                        {"text": "Otro producto 1 10 10", "line_id": "b"},
                    ],
                }
            ],
            "palabras_muestra": [{"text": "x", "page": 1, "left": 0, "top": 0, "width": 1, "height": 1}] * 10,
        }
        r = parsear_line_items_documento("", ocr, [])
        self.assertGreaterEqual(len(r["items"]), 2)
        self.assertTrue(r["quality"]["tabular_layout_detected"])

    def test_fallback_sin_ocr_estructurado(self):
        texto = f"Linea\n{LINEA_ITEM_UNIDADES}\n"
        cab, lineas, _ = parsear_texto_factura(texto)
        self.assertGreaterEqual(len(lineas), 1)
        r = parsear_line_items_documento(texto, None, lineas)
        self.assertTrue(r["quality"]["fallback_used"])
        self.assertEqual(r["quality"]["source"], "heuristic_fallback")
        self.assertEqual(r["quality"]["item_count"], len(lineas))
        self.assertEqual(r["items"][0]["source"], "heuristic_fallback")

    def test_evidencia_y_banda_presentes(self):
        cab, lineas, _ = parsear_texto_factura(f"X\n{LINEA_ITEM_SIMPLE}\n")
        r = parsear_line_items_documento("", None, lineas)
        c = r["items"][0]["campos"]["cantidad"]
        self.assertIn("banda", c)
        self.assertIn("confidence", c)
        self.assertIn("evidencia", c)

    def test_resumen_quality(self):
        r = parsear_line_items_documento("", None, [])
        self.assertIn("schema_version", r["quality"])
        self.assertIn("heuristic_line_count", r["quality"])
        self.assertEqual(r["quality"]["item_count"], 0)


class LineItemsIntegrationTests(SimpleTestCase):
    def test_analizar_pdf_incluye_line_items_y_quality(self):
        from factura_compra_captura.ocr.heuristic_pdf import analizar_archivo_factura

        texto = """
        Factura C
        CUIT: 20-12345678-9
        Comp. Nro 0001-00000001
        Importe Total: $ 100,00
        Producto test 2 50,00 100,00
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name
        try:
            c = canvas.Canvas(path, pagesize=(400, 300))
            for i, line in enumerate(texto.strip().split("\n")):
                c.drawString(40, 280 - i * 14, line.strip()[:90])
            c.save()
            out = analizar_archivo_factura(path, "application/pdf")
        finally:
            os.unlink(path)
        de = out["raw"].get("document_engine_v1")
        self.assertIsNotNone(de)
        self.assertGreaterEqual(de.get("version"), 5)
        self.assertIn("line_items", de["parsed"])
        self.assertIn("line_items_quality", de)
        self.assertIn("schema_version", de["line_items_quality"])
        self.assertGreaterEqual(len(out["lineas_sugeridas"]), 0)
