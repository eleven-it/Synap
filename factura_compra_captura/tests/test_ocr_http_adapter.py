from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from factura_compra_captura.ocr.base import OcrAdapterError
from factura_compra_captura.ocr.http_adapter import HttpOcrAdapter


class HttpOcrAdapterTests(SimpleTestCase):
    @override_settings(FACTURA_COMPRA_OCR_HTTP_URL="")
    def test_url_requerida(self):
        adp = HttpOcrAdapter()
        with self.assertRaises(OcrAdapterError):
            adp.extract(ruta_archivo=__file__, mime_type="application/pdf")

    @override_settings(
        FACTURA_COMPRA_OCR_HTTP_URL="https://ocr.example.local/extract",
        FACTURA_COMPRA_OCR_HTTP_TIMEOUT=5,
    )
    @patch("factura_compra_captura.ocr.http_adapter.requests.post")
    def test_parseo_payload(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "text": "texto detectado",
            "confidence": 0.75,
            "header": {"nro_comprobante_texto": "0001-00001234"},
            "lines": [{"cantidad": "1", "precio_unitario": "100.00"}],
        }
        mock_post.return_value = resp
        adp = HttpOcrAdapter()
        out = adp.extract(ruta_archivo=__file__, mime_type="application/pdf")
        self.assertEqual(out.texto_plano, "texto detectado")
        self.assertAlmostEqual(out.confianza_global, 0.75, places=2)
        self.assertEqual(out.campos_cabecera.get("nro_comprobante_texto"), "0001-00001234")
        self.assertEqual(len(out.lineas_sugeridas), 1)
