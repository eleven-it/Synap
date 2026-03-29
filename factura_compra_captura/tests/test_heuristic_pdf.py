import os
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from reportlab.pdfgen import canvas

from factura_compra_captura.ocr.heuristic_pdf import (
    analizar_archivo_factura,
    parsear_texto_factura,
)
from factura_compra_captura.tests.test_documento_upload import _mini_jpeg_bytes


class ParsearTextoFacturaTests(SimpleTestCase):
    def test_detecta_cuit_nro_fecha_total(self):
        texto = """
        PROVEEDOR DEMO SRL
        CUIT: 30-70185500-8
        Factura A  Fecha de emisión: 15/03/2026
        Comp. Nro 0001-00001234
        Total $ 12.345,67
        """
        cab, lineas, conf = parsear_texto_factura(texto)
        self.assertEqual(cab.get("nro_comprobante_texto"), "0001-00001234")
        self.assertEqual(cab.get("fecha_comprobante_texto"), "15/03/2026")
        self.assertEqual(cab.get("proveedor_cuit_texto"), "30-70185500-8")
        self.assertEqual(cab.get("importe_total_texto"), "12345.67")
        self.assertEqual(cab.get("tipo_factura"), "FA")
        self.assertGreater(conf, 0.5)

    def test_vacio_devuelve_cero_confianza(self):
        cab, lineas, conf = parsear_texto_factura("")
        self.assertEqual(cab, {})
        self.assertEqual(lineas, [])
        self.assertEqual(conf, 0.0)

    def test_fecha_emision_no_es_razon_social(self):
        texto = """
        Fecha de Emisión: 01/02/2026
        CUIT 30-70185500-8
        PROVEEDOR EJEMPLO S.R.L.
        0001-00001234
        Total $ 1.234,56
        """
        cab, _, _ = parsear_texto_factura(texto)
        self.assertEqual(cab.get("proveedor_texto"), "PROVEEDOR EJEMPLO S.R.L.")
        self.assertNotEqual(cab.get("proveedor_texto"), "Fecha de Emisión:")

    def test_total_suelto_en_linea(self):
        texto = "X\nTotal $ 999,50\n"
        cab, _, _ = parsear_texto_factura(texto)
        self.assertEqual(cab.get("importe_total_texto"), "999.50")

    def test_dedupe_lineas_pdf_multicopia(self):
        """Mismo ítem repetido por ORIGINAL/DUPLICADO/TRIPLICADO en texto concatenado → una línea."""
        bloque = (
            "HONORARIOS FEBRERO 2026 1,00 unidades 3154720,97 3154720,970,00 0,00\n"
        )
        texto = (bloque * 3).strip()
        cab, lineas, _ = parsear_texto_factura(texto)
        self.assertEqual(len(lineas), 1)
        self.assertEqual(cab.get("lineas_repetidas_omitidas"), 2)

    def test_tipo_factura_cod_en_lineas_distintas(self):
        """COD y 011 separados: texto compactado permite detectar FC."""
        texto = "FACTURA\nCOD.\n011\n"
        cab, _, _ = parsear_texto_factura(texto)
        self.assertEqual(cab.get("tipo_factura"), "FC")

    def test_cod_arca_011_y_letra_sola_factura(self):
        """ARCA: 'COD. 011' (Factura C) sin texto 'Factura C' en una línea; o letra C suelta junto a FACTURA."""
        texto_cod = """
        C
        COD. 011
        FACTURA
        Punto de Venta: 00004
        """
        cab, _, _ = parsear_texto_factura(texto_cod)
        self.assertEqual(cab.get("tipo_factura"), "FC")

        texto_letra = """
        FACTURA
        C
        Comp. Nro: 0001 00000001
        """
        cab2, _, _ = parsear_texto_factura(texto_letra)
        self.assertEqual(cab2.get("tipo_factura"), "FC")

    def test_layout_afip_comp_nro_pv_unidades_y_montos(self):
        """Factura C típica: Comp. Nro sin espacio, período en una línea, emisión suelta, total en bloque."""
        texto = """
        Razon Social:
        PAREDES CLAUDIO SEBASTIAN
        FACTURA C
        Fecha de Emisión:
        ORIGINAL
        Período Facturado Desde: Hasta: Fecha de Vto. para el pago:
        01/02/2026 28/02/2026 03/03/2026
        27/02/2026
        20270909575
        ADMINISTRANET S. A. S.
        Punto de Venta: Comp. Nro:00004 00000037
        Código Producto / Servicio Cantidad U. Medida Precio Unit.
        HONORARIOS FEBRERO 2026 1,00 unidades 3154720,97 3154720,970,00 0,00
        Subtotal: $
        Importe Otros Tributos: $
        Importe Total: $
        3154720,97
        CAE N°:
        """
        cab, lineas, _ = parsear_texto_factura(texto)
        self.assertEqual(cab.get("nro_comprobante_texto"), "00004-00000037")
        self.assertEqual(cab.get("fecha_comprobante_texto"), "27/02/2026")
        self.assertEqual(cab.get("proveedor_cuit_texto"), "20-27090957-5")
        self.assertEqual(cab.get("proveedor_texto"), "PAREDES CLAUDIO SEBASTIAN")
        self.assertEqual(cab.get("tipo_factura"), "FC")
        self.assertEqual(cab.get("importe_total_texto"), "3154720.97")
        self.assertEqual(len(lineas), 1)
        self.assertIn("HONORARIOS", lineas[0]["descripcion"])


class HeuristicPdfArchivoTests(SimpleTestCase):
    def _pdf_con_texto(self) -> bytes:
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=(400, 200))
        c.drawString(40, 160, "Razon Social SA")
        c.drawString(40, 140, "CUIT 30-70185500-8")
        c.drawString(40, 120, "Fecha 05/02/2025")
        c.drawString(40, 100, "0001-00009999")
        c.drawString(40, 80, "Total 500,25")
        c.save()
        return buf.getvalue()

    def test_pdf_generado_extrae_campos(self):
        data = self._pdf_con_texto()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            out = analizar_archivo_factura(path, "application/pdf")
        finally:
            os.unlink(path)
        self.assertEqual(out["raw"]["motor"], "heuristic")
        self.assertEqual(out["raw"]["extraccion"], "pypdf")
        self.assertGreater(out["confianza_global"], 0.2)
        cab = out["campos_cabecera"]
        self.assertEqual(cab.get("proveedor_cuit_texto"), "30-70185500-8")
        self.assertEqual(cab.get("nro_comprobante_texto"), "0001-00009999")


@patch("pytesseract.image_to_string")
class HeuristicImagenTesseractTests(SimpleTestCase):
    def test_jpeg_con_ocr_mockeado_parsea_cabecera(self, mock_ts):
        mock_ts.return_value = """
        PROVEEDOR FOTO SA
        CUIT 30-70185500-8
        Fecha 15/03/2026
        0001-00001111
        Total $ 100,50
        """
        data = _mini_jpeg_bytes()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            out = analizar_archivo_factura(path, "image/jpeg")
        finally:
            os.unlink(path)
        self.assertEqual(out["raw"]["extraccion"], "tesseract")
        self.assertEqual(out["campos_cabecera"].get("nro_comprobante_texto"), "0001-00001111")
        mock_ts.assert_called_once()

    def test_tesseract_deshabilitado_no_llama_pytesseract(self, mock_ts):
        data = _mini_jpeg_bytes()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            out = analizar_archivo_factura(
                path,
                "image/jpeg",
                tesseract_enabled=False,
            )
        finally:
            os.unlink(path)
        mock_ts.assert_not_called()
        self.assertEqual(out["raw"].get("extraccion"), "deshabilitada")
        self.assertEqual(out["confianza_global"], 0.0)
