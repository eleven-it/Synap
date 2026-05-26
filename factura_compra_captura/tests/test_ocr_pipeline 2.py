from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.api import views as compras_api_views
from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
from factura_compra_captura.ocr.base import OcrAdapterError
from factura_compra_captura.tests.compras_test_permissions import (
    otorgar_permisos_compras,
)
from factura_compra_captura.tests.test_documento_upload import _mini_jpeg_bytes


class _BoomOcrAdapter:
    def extract(self, **kwargs):
        raise OcrAdapterError(
            "TEST_FORZADO",
            "Fallo simulado del motor OCR (prueba).",
        )


@override_settings(
    FACTURA_COMPRA_OCR_SYNC=True,
    FACTURA_COMPRA_OCR_TESSERACT_ENABLED=False,
)
class OcrFallidoNoBloqueaExpedienteTests(TestCase):
    """TC-OCR-02: fallo OCR; expediente sigue editable en borrador."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._throttle_save = compras_api_views.DocumentoFuenteListCreateAPIView.throttle_classes
        compras_api_views.DocumentoFuenteListCreateAPIView.throttle_classes = []

    @classmethod
    def tearDownClass(cls):
        compras_api_views.DocumentoFuenteListCreateAPIView.throttle_classes = cls._throttle_save
        super().tearDownClass()

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="OCR Fail Test",
            razon_social="OCR Fail SA",
            identificador_fiscal="20445556667",
        )
        self.user = UsuarioExtendido.objects.create_user(
            email="ocr-fail@test.local",
            nombre="O",
            password="x",
        )
        self.user.uid = "uid-ocr-fail"
        self.user.save()
        otorgar_permisos_compras(self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        r = self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        self.eid = r.data["id"]

    @patch(
        "factura_compra_captura.ocr.pipeline.get_ocr_adapter",
        return_value=_BoomOcrAdapter(),
    )
    def test_tc_ocr_02_fallo_documento_expediente_borrador(self, _mock_get):
        f = SimpleUploadedFile(
            "f.jpg",
            _mini_jpeg_bytes(),
            content_type="image/jpeg",
        )
        r = self.client.post(
            f"/api/compras/expedientes/{self.eid}/documentos/",
            {"archivo": f},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            r.data["estado_procesamiento"],
            DocumentoFuente.EstadoProcesamiento.FALLIDO,
        )
        exp = ExpedienteFacturaCompra.objects.get(pk=self.eid)
        self.assertEqual(exp.estado, ExpedienteFacturaCompra.Estado.BORRADOR)
        self.assertIn("ocr_ultimo_error", exp.metadata)

    def test_reintento_ocr(self):
        with patch(
            "factura_compra_captura.ocr.pipeline.get_ocr_adapter",
            return_value=_BoomOcrAdapter(),
        ):
            f = SimpleUploadedFile(
                "f.jpg",
                _mini_jpeg_bytes(),
                content_type="image/jpeg",
            )
            r0 = self.client.post(
                f"/api/compras/expedientes/{self.eid}/documentos/",
                {"archivo": f},
                format="multipart",
            )
        did = r0.data["id"]
        r1 = self.client.post(
            f"/api/compras/expedientes/{self.eid}/documentos/{did}/reintentar-ocr/",
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(
            r1.data["estado_procesamiento"],
            DocumentoFuente.EstadoProcesamiento.COMPLETADO,
        )
        exp = ExpedienteFacturaCompra.objects.get(pk=self.eid)
        self.assertEqual(exp.estado, ExpedienteFacturaCompra.Estado.OCR_COMPLETADO)
