"""Stage 1: preprocesado OpenCV + OCR estructurado TSV (sin cambiar contrato OcrExtractResult)."""

from __future__ import annotations

import os
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image

from factura_compra_captura.ocr.image_preprocess import preprocesar_imagen_factura
from factura_compra_captura.ocr.tesseract_structured import construir_resumen_desde_dict_tsv
from factura_compra_captura.tests.test_documento_upload import _mini_jpeg_bytes


class PreprocessFallbackTests(SimpleTestCase):
    def test_preprocesar_factura_usa_original_si_opencv_falla(self):
        """Si un paso de OpenCV falla, se conserva la imagen y fallback=True."""
        try:
            import cv2
        except ImportError:
            self.skipTest("OpenCV no instalado (opencv-python-headless)")

        img = Image.new("RGB", (120, 120), color=(240, 240, 240))
        with patch.object(cv2, "createCLAHE", side_effect=RuntimeError("simulado")):
            out, meta = preprocesar_imagen_factura(img)
        self.assertIs(meta.get("fallback"), True)
        self.assertEqual(out.size, img.size)


class TsvParsingTests(SimpleTestCase):
    def test_construir_resumen_desde_dict_tsv_agrupa_lineas(self):
        data = {
            "text": ["Hola", "mundo", ""],
            "conf": [92, 88, -1],
            "left": [10, 50, 0],
            "top": [5, 5, 0],
            "width": [30, 40, 0],
            "height": [12, 12, 0],
            "page_num": [1, 1, 1],
            "block_num": [0, 0, 0],
            "par_num": [0, 0, 0],
            "line_num": [0, 0, 0],
        }
        res = construir_resumen_desde_dict_tsv(data)
        self.assertEqual(res["word_count"], 2)
        self.assertIsNotNone(res.get("mean_confidence"))
        self.assertGreaterEqual(len(res.get("palabras_muestra", [])), 1)


class StructuredOcrIntegrationTests(SimpleTestCase):
    def test_legacy_sin_document_engine_v1_en_raw(self):
        from factura_compra_captura.ocr.heuristic_pdf import analizar_archivo_factura

        buf = BytesIO(_mini_jpeg_bytes())
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(buf.getvalue())
            path = tmp.name
        try:
            out = analizar_archivo_factura(
                path,
                "image/jpeg",
                tesseract_enabled=False,
                engine_mode="legacy",
            )
        finally:
            os.unlink(path)
        self.assertNotIn("document_engine_v1", out["raw"])

    @patch(
        "factura_compra_captura.ocr.heuristic_pdf._tesseract_string_from_pil",
        return_value="",
    )
    @patch(
        "factura_compra_captura.ocr.tesseract_structured.construir_ocr_structured_desde_imagen"
    )
    def test_structured_ocr_incluye_ocr_structured_en_raw(
        self, mock_struct: object, _mock_tesseract_str: object
    ) -> None:
        from factura_compra_captura.ocr.heuristic_pdf import analizar_archivo_factura

        mock_struct.return_value = {
            "fuente": "tesseract_tsv",
            "word_count": 3,
            "pages": [],
        }
        buf = BytesIO(_mini_jpeg_bytes())
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(buf.getvalue())
            path = tmp.name
        try:
            out = analizar_archivo_factura(
                path,
                "image/jpeg",
                tesseract_enabled=True,
                engine_mode="structured_ocr",
            )
        finally:
            os.unlink(path)
        de = out["raw"].get("document_engine_v1")
        self.assertIsNotNone(de)
        self.assertEqual(de.get("engine_mode"), "structured_ocr")
        self.assertIn("ocr_structured", de)
        self.assertEqual(de["ocr_structured"]["word_count"], 3)
        self.assertIn("classification", de)
        self.assertIn("parsed", de)
        mock_struct.assert_called_once()

    @patch(
        "factura_compra_captura.ocr.heuristic_pdf._tesseract_string_from_pil",
        return_value="",
    )
    def test_preprocess_only_incluye_preprocess_sin_ocr_structured(
        self, _mock_tesseract_str: object
    ) -> None:
        from factura_compra_captura.ocr.heuristic_pdf import analizar_archivo_factura

        buf = BytesIO(_mini_jpeg_bytes())
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(buf.getvalue())
            path = tmp.name
        try:
            out = analizar_archivo_factura(
                path,
                "image/jpeg",
                tesseract_enabled=True,
                engine_mode="preprocess_only",
            )
        finally:
            os.unlink(path)
        de = out["raw"].get("document_engine_v1")
        self.assertIsNotNone(de)
        self.assertEqual(de.get("engine_mode"), "preprocess_only")
        self.assertIn("preprocess", de)
        self.assertIsNone(de.get("ocr_structured"))
        self.assertIn("classification", de)
        self.assertIn("parsed", de)

    @patch(
        "factura_compra_captura.ocr.heuristic_pdf._tesseract_string_from_pil",
        return_value="texto",
    )
    def test_engine_mode_desconocido_normaliza_a_legacy_con_stage2(
        self, _mock_tesseract_str: object
    ) -> None:
        """Valores no reconocidos → motor legacy sin preprocess; Stage 2 sí añade classification."""
        from factura_compra_captura.ocr.heuristic_pdf import analizar_archivo_factura

        buf = BytesIO(_mini_jpeg_bytes())
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(buf.getvalue())
            path = tmp.name
        try:
            out = analizar_archivo_factura(
                path,
                "image/jpeg",
                tesseract_enabled=True,
                engine_mode="modo_inexistente",
            )
        finally:
            os.unlink(path)
        de = out["raw"].get("document_engine_v1")
        self.assertIsNotNone(de)
        self.assertEqual(de.get("engine_mode"), "legacy")
        self.assertNotIn("preprocess", de)
        self.assertIn("classification", de)
        self.assertIn("parsed", de)
