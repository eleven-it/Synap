"""Stage 4: motor de validación interna (no bloqueante)."""

from __future__ import annotations

from django.test import SimpleTestCase

from factura_compra_captura.services.document_validation_engine import (
    ejecutar_validaciones_documento,
)


def _header_campo(valor: str | None) -> dict:
    return {
        "valor": valor,
        "confidence": 0.7,
        "banda": "media",
        "source": "heuristic",
        "evidencia": {"schema_version": 1, "page": None, "bbox": None, "raw_text": str(valor or "")},
    }


def _item(cant: str, precio: str, total_implied: float | None = None) -> dict:
    return {
        "item_index": 0,
        "source": "structured",
        "campos": {
            "descripcion": _header_campo("Producto"),
            "cantidad": _header_campo(cant),
            "precio_unitario": _header_campo(precio),
        },
    }


class ValidationEngineUnitTests(SimpleTestCase):
    def _base_de(
        self,
        *,
        lista_faltantes: list[str] | None = None,
        total_val: str | None = "100.00",
        proveedor_val: str | None = "EMPRESA SA",
        tipo_doc: str = "invoice_probable",
        items: list | None = None,
        item_count: int | None = None,
        checks: list | None = None,
    ) -> dict:
        lf = lista_faltantes if lista_faltantes is not None else []
        its = items if items is not None else [
            _item("2", "50.00"),
        ]
        ic = item_count if item_count is not None else len(its)
        return {
            "version": 5,
            "classification": {
                "tipo_documento": tipo_doc,
                "confidence": 0.85,
            },
            "parsed": {
                "header": {
                    "proveedor": _header_campo(proveedor_val),
                    "tipo_factura": _header_campo("FA"),
                    "punto_venta": _header_campo("0001"),
                    "numero": _header_campo("00000001"),
                    "fecha": _header_campo("01/01/2026"),
                    "total": _header_campo(total_val),
                },
                "header_quality": {
                    "campos_criticos": {
                        "lista": lf,
                        "cantidad": len(lf),
                        "total_campos": 6,
                    },
                    "consistencia_legacy": {
                        "checks": checks or [],
                        "score": 1.0,
                        "pares_comparados": 0,
                    },
                },
                "line_items": its,
            },
            "line_items_quality": {
                "schema_version": 1,
                "item_count": ic,
                "heuristic_line_count": ic,
            },
        }

    def test_documento_consistente_sin_errores_graves(self):
        de = self._base_de()
        r = ejecutar_validaciones_documento(de)
        self.assertFalse(r["validation_summary"]["has_errors"])
        codes = [v["codigo"] for v in r["validations"]]
        self.assertNotIn("cross.suma_lineas_vs_total_grave", codes)

    def test_campos_criticos_disparan_warning(self):
        de = self._base_de(lista_faltantes=["fecha", "total"])
        r = ejecutar_validaciones_documento(de)
        codes = [v["codigo"] for v in r["validations"]]
        self.assertIn("header.campos_criticos_faltantes", codes)
        w = [v for v in r["validations"] if v["codigo"] == "header.campos_criticos_faltantes"][0]
        self.assertEqual(w["severidad"], "warning")

    def test_cantidad_no_positiva(self):
        it = _item("-1", "10")
        it["item_index"] = 0
        de = self._base_de(items=[it], total_val="10")
        r = ejecutar_validaciones_documento(de)
        codes = [v["codigo"] for v in r["validations"]]
        self.assertIn("lineas.cantidad_no_positiva", codes)

    def test_suma_lineas_vs_total(self):
        # 97 vs 100 → ~3 % de diferencia (warning, no grave)
        de = self._base_de(
            items=[_item("1", "97.00")],
            total_val="100.00",
        )
        r = ejecutar_validaciones_documento(de)
        codes = [v["codigo"] for v in r["validations"]]
        self.assertIn("cross.suma_lineas_vs_total", codes)

    def test_suma_grave_error(self):
        de = self._base_de(
            items=[_item("1", "10.00")],
            total_val="1000.00",
        )
        r = ejecutar_validaciones_documento(de)
        codes = [v["codigo"] for v in r["validations"]]
        self.assertIn("cross.suma_lineas_vs_total_grave", codes)
        self.assertTrue(r["validation_summary"]["has_errors"])

    def test_sin_lineas_info(self):
        de = self._base_de(items=[], item_count=0)
        de["parsed"]["line_items"] = []
        de["line_items_quality"]["item_count"] = 0
        r = ejecutar_validaciones_documento(de)
        codes = [v["codigo"] for v in r["validations"]]
        self.assertIn("lineas.sin_items", codes)

    def test_solo_warnings_posibles(self):
        de = self._base_de(lista_faltantes=["fecha"])
        de["parsed"]["header"]["total"] = _header_campo(None)
        r = ejecutar_validaciones_documento(de)
        self.assertFalse(r["validation_summary"]["has_errors"])

    def test_evidencia_schema_en_validaciones(self):
        de = self._base_de(lista_faltantes=["numero"])
        for v in ejecutar_validaciones_documento(de)["validations"]:
            self.assertIn("evidencia", v)
            self.assertIn("schema_version", v["evidencia"])

    def test_consistencia_legacy_fallida(self):
        de = self._base_de(
            checks=[
                {
                    "codigo": "importe_total",
                    "ok": False,
                    "legacy": "100",
                    "header": "200",
                    "detalle": "x",
                }
            ]
        )
        r = ejecutar_validaciones_documento(de)
        codes = [v["codigo"] for v in r["validations"]]
        self.assertIn("cross.consistencia_legacy_fallida", codes)


class ValidationIntegrationTests(SimpleTestCase):
    def test_analizar_pdf_incluye_validations(self):
        import os
        import tempfile

        from factura_compra_captura.ocr.heuristic_pdf import analizar_archivo_factura
        from reportlab.pdfgen import canvas

        texto = """
        Factura A
        PROVEEDOR X
        CUIT: 20-12345678-9
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
        de = out["raw"]["document_engine_v1"]
        self.assertGreaterEqual(de.get("version"), 5)
        self.assertIn("validations", de)
        self.assertIn("validation_summary", de)
        self.assertIn("counts", de["validation_summary"])
