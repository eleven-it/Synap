"""Stage 7: contexto de revisión API y append de correcciones de analista."""

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
from factura_compra_captura.tests.compras_test_permissions import (
    otorgar_permisos_compras,
)
from factura_compra_captura.tests.test_documento_upload import _mini_jpeg_bytes


def _de_muestra():
    return {
        "version": 7,
        "document_score": 0.82,
        "workflow_facing_summary": {
            "schema_version": 1,
            "headline": "Documento procesado; sin alertas graves en el motor de validación.",
            "review_recommended": False,
            "template_id": "demo_cuit_30701855008",
            "metrics_digest": "v7|tmpl:x|review:0",
        },
        "workflow_signals": {
            "schema_version": 1,
            "supplier_template_id": "demo_cuit_30701855008",
            "template_matched": True,
            "suggested_review": False,
            "blocking_issues": False,
        },
        "validation_summary": {
            "schema_version": 1,
            "counts": {"info": 0, "warning": 1, "error": 0},
            "has_errors": False,
            "has_warnings": True,
            "health_score": 0.9,
        },
        "document_engine_metrics": {
            "schema_version": 1,
            "template_performance": {
                "matched": True,
                "template_id": "demo_cuit_30701855008",
                "match_confidence": 0.9,
                "header_fields_extracted_count": 1,
                "line_supplement_count": 0,
            },
        },
        "parsed": {
            "header": {
                "proveedor": {
                    "valor": "ACME SA",
                    "confidence": 0.8,
                    "banda": "alta",
                    "source": "heuristic",
                    "evidencia": {"schema_version": 1, "raw_text": "ACME SA en doc"},
                },
            },
            "line_items": [
                {
                    "item_index": 0,
                    "source": "heuristic",
                    "campos": {
                        "descripcion": {
                            "valor": "Item A",
                            "confidence": 0.7,
                            "evidencia": {"raw_text": "Item A línea"},
                        },
                    },
                }
            ],
        },
    }


@override_settings(
    FACTURA_COMPRA_OCR_SYNC=True,
    FACTURA_COMPRA_OCR_TESSERACT_ENABLED=False,
)
class RevisionEngineContextAPITests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Rev Eng Test",
            razon_social="Rev Eng Test SA",
            identificador_fiscal="20911112222",
        )
        self.user = UsuarioExtendido.objects.create_user(
            email="rev-eng@test.local",
            nombre="Rev",
            password="x",
        )
        self.user.uid = "uid-rev-eng"
        self.user.save()
        otorgar_permisos_compras(self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.expediente = ExpedienteFacturaCompra.objects.create(
            empresa=self.empresa,
        )
        f = SimpleUploadedFile(
            "foto.jpg",
            _mini_jpeg_bytes(),
            content_type="image/jpeg",
        )
        self.doc = DocumentoFuente.objects.create(
            expediente=self.expediente,
            archivo=f,
            nombre_original="foto.jpg",
            mime_type="image/jpeg",
            tipo_archivo=DocumentoFuente.TipoArchivo.IMAGEN,
            estado_procesamiento=DocumentoFuente.EstadoProcesamiento.COMPLETADO,
            resultado_ocr={
                "texto_plano": "x",
                "confianza_global": 0.5,
                "campos_cabecera": {},
                "lineas_sugeridas": [],
                "raw": {"document_engine_v1": _de_muestra()},
            },
        )

    def test_r1_revision_engine_context_en_get(self):
        r = self.client.get(f"/api/compras/expedientes/{self.expediente.pk}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ctx = r.data.get("revision_engine_context")
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.get("schema_version"), 1)
        self.assertEqual(ctx.get("engine_version"), 7)
        self.assertIn("workflow_facing_summary", ctx)
        self.assertIn("header_campos", ctx)
        self.assertTrue(any(c.get("campo") == "proveedor" for c in ctx["header_campos"]))
        self.assertEqual(len(ctx.get("line_items_ui") or []), 1)

    def test_r2_workflow_facing_headline(self):
        r = self.client.get(f"/api/compras/expedientes/{self.expediente.pk}/")
        ctx = r.data.get("revision_engine_context") or {}
        wfs = ctx.get("workflow_facing_summary") or {}
        self.assertIn("headline", wfs)

    def test_r3_r4_evidencia_cabecera_y_linea(self):
        r = self.client.get(f"/api/compras/expedientes/{self.expediente.pk}/")
        ctx = r.data.get("revision_engine_context") or {}
        prov = next(x for x in ctx["header_campos"] if x["campo"] == "proveedor")
        self.assertEqual(prov.get("confidence"), 0.8)
        self.assertIn("ACME", prov.get("evidencia_preview") or "")
        li0 = ctx["line_items_ui"][0]
        self.assertIn("descripcion", li0["campos"])
        self.assertIn("Item A", li0["campos"]["descripcion"].get("evidencia_preview") or "")

    def test_r5_analyst_feedback_append(self):
        r = self.client.patch(
            f"/api/compras/expedientes/{self.expediente.pk}/",
            {
                "analyst_feedback_append": [
                    {
                        "campo": "importe_total",
                        "valor_anterior": "100",
                        "valor_nuevo": "101",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r2 = self.client.get(f"/api/compras/expedientes/{self.expediente.pk}/")
        md = r2.data.get("metadata") or {}
        af = md.get("analyst_feedback") or {}
        self.assertEqual(len(af.get("corrections") or []), 1)
        self.assertEqual(af["corrections"][0]["campo"], "importe_total")

    def test_r6_sin_documento_revision_engine_context_null(self):
        e2 = ExpedienteFacturaCompra.objects.create(empresa=self.empresa)
        r = self.client.get(f"/api/compras/expedientes/{e2.pk}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data.get("revision_engine_context"))


class RevisionEngineContextSerializerUnitTests(SimpleTestCase):
    def test_backward_compatibility_campos_serializador(self):
        from factura_compra_captura.api.serializers import ExpedienteFacturaCompraSerializer

        ser = ExpedienteFacturaCompraSerializer()
        names = list(ser.fields.keys())
        for key in ("id", "metadata", "lineas", "documentos_fuente", "revision_engine_context"):
            self.assertIn(key, names)
