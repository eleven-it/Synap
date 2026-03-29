"""Tests detector fiscal (tipo letra + código AFIP + mapeo AdministraNET)."""

from __future__ import annotations

from django.test import SimpleTestCase

from factura_compra_captura.services.fiscal_type_detector import (
    detectar_tipo_fiscal,
    normalizar_codigo_cbte_afip,
)


class FiscalTypeDetectorTests(SimpleTestCase):
    def test_d1_c_mas_cod_011(self):
        texto = """
        FACTURA
        C
        COD. 011
        """
        r = detectar_tipo_fiscal(texto, None, None)
        self.assertEqual(r.get("adminnet_tipo_factura"), "FC")
        self.assertEqual(r.get("afip_cbte_code"), 11)
        self.assertEqual(r.get("fiscal_letter"), "C")
        self.assertEqual(r.get("consistency_status"), "consistent")

    def test_d2_solo_cod_011(self):
        texto = "FACTURA\nCOD.\n011\n"
        r = detectar_tipo_fiscal(texto, None, None)
        self.assertEqual(r.get("adminnet_tipo_factura"), "FC")
        self.assertEqual(r.get("afip_cbte_code"), 11)

    def test_d3_factura_c_texto(self):
        texto = "FACTURA C\nCUIT 20-12345678-9\n"
        r = detectar_tipo_fiscal(texto, None, None)
        self.assertEqual(r.get("adminnet_tipo_factura"), "FC")
        self.assertEqual(r.get("fiscal_letter"), "C")

    def test_d4_mismatch_letra_a_cod_011(self):
        texto = "FACTURA A\nCOD. 011\n"
        r = detectar_tipo_fiscal(texto, None, None)
        self.assertEqual(r.get("consistency_status"), "inconsistent")
        self.assertEqual(r.get("adminnet_tipo_factura"), "FC")
        self.assertLess(r.get("confidence", 1.0), 0.95)

    def test_d5_sin_senal(self):
        texto = "documento sin tipo ni codigo claro\n"
        r = detectar_tipo_fiscal(texto, None, None)
        self.assertIsNone(r.get("adminnet_tipo_factura"))
        self.assertEqual(r.get("source"), "unknown")

    def test_d6_vacio_nunca_fa(self):
        r = detectar_tipo_fiscal("", None, None)
        self.assertIsNone(r.get("adminnet_tipo_factura"))
        self.assertNotEqual(r.get("adminnet_tipo_factura"), "FA")

    def test_d7_ocr_linea_estructurada(self):
        ocr = {
            "pages": [
                {
                    "page_num": 1,
                    "lines": [
                        {"text": "FACTURA C", "line_id": "0"},
                    ],
                }
            ]
        }
        r = detectar_tipo_fiscal("x", ocr, None)
        self.assertEqual(r.get("adminnet_tipo_factura"), "FC")
        self.assertIn("structured", r.get("source", ""))

    def test_d8_texto_ruidoso_cod(self):
        texto = "foo COD.. 011 bar"
        r = detectar_tipo_fiscal(texto, None, None)
        self.assertEqual(r.get("afip_cbte_code"), 11)

    def test_d9_normaliza_codigo(self):
        self.assertEqual(normalizar_codigo_cbte_afip("011"), 11)
        self.assertEqual(normalizar_codigo_cbte_afip("11"), 11)
        self.assertEqual(normalizar_codigo_cbte_afip("0011"), 11)

    def test_d10_adminnet_mapping_ref(self):
        r = detectar_tipo_fiscal("COD. 006\n", None, None)
        m = r.get("adminnet_mapping") or {}
        self.assertEqual(m.get("adminnet_tipo_factura"), "FB")
        self.assertIn("AFIP_FECAEDetRequest_CAMPOS", m.get("doc_ref", ""))


class HeaderParserFiscalIntegrationTests(SimpleTestCase):
    def test_d11_parseo_cabecera_c_011(self):
        from factura_compra_captura.services.header_parser import parsear_cabecera_documento

        cab = {"tipo_factura": None}
        texto = "FACTURA\nC\nCOD. 011\n"
        h = parsear_cabecera_documento(texto, None, cab)
        self.assertEqual(h["tipo_factura"]["valor"], "FC")

    def test_d12_sin_tipo_no_fa(self):
        from factura_compra_captura.services.header_parser import parsear_cabecera_documento

        texto = "solo texto sin comprobante fiscal tipico\n"
        h = parsear_cabecera_documento(texto, None, {})
        self.assertIsNone(h["tipo_factura"]["valor"])
