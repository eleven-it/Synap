from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.api import views as compras_api_views
from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
from factura_compra_captura.tests.compras_test_permissions import (
    otorgar_permisos_compras,
)


def _mini_jpeg_bytes() -> bytes:
    """JPEG 1x1 mínimo válido."""
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x03\x02\x02\x03\x02\x02\x03\x03\x03\x03\x04\x03\x03"
        b"\x04\x05\x08\x05\x05\x04\x04\x05\n\x07\x07\x06\x08\x0c\n\x0c\x0c\x0b\n"
        b"\x0b\x0b\r\x0e\x12\x10\r\x0e\x11\x0e\x0b\x0b\x10\x16\x10\x11\x13\x14\x15"
        b"\x15\x15\x0c\x0f\x17\x18\x16\x14\x18\x12\x14\x15\x14\xff\xc0\x00\x0b\x08"
        b"\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01"
        b"\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06"
        b"\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05"
        b"\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"
        b"\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17"
        b"\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85"
        b"\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5"
        b"\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5"
        b"\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4"
        b"\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda"
        b"\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9"
    )


@override_settings(
    FACTURA_COMPRA_OCR_SYNC=True,
    FACTURA_COMPRA_OCR_TESSERACT_ENABLED=False,
)
class DocumentoUploadAPITests(TestCase):
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
            nombre="Doc Upload Test",
            razon_social="Doc Upload Test SA",
            identificador_fiscal="20334445556",
        )
        self.user = UsuarioExtendido.objects.create_user(
            email="doc-up@test.local",
            nombre="Doc",
            password="x",
        )
        self.user.uid = "uid-doc-up"
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

    def test_tc_cap_01_subida_jpeg_crea_documento_y_ocr(self):
        f = SimpleUploadedFile(
            "foto.jpg",
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
            DocumentoFuente.EstadoProcesamiento.COMPLETADO,
        )
        exp = ExpedienteFacturaCompra.objects.get(pk=self.eid)
        self.assertEqual(exp.estado, ExpedienteFacturaCompra.Estado.OCR_COMPLETADO)

    def test_tc_cap_02_pdf_multipart_ok(self):
        pdf = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
        f = SimpleUploadedFile("doc.pdf", pdf, content_type="application/pdf")
        r = self.client.post(
            f"/api/compras/expedientes/{self.eid}/documentos/",
            {"archivo": f},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["tipo_archivo"], DocumentoFuente.TipoArchivo.PDF)

    def test_mime_no_permitido_400(self):
        f = SimpleUploadedFile(
            "x.exe",
            b"MZ\x90\x00",
            content_type="application/octet-stream",
        )
        r = self.client.post(
            f"/api/compras/expedientes/{self.eid}/documentos/",
            {"archivo": f},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data.get("codigo"), "mime_no_permitido")

    @override_settings(FACTURA_COMPRA_DOCUMENTO_MAX_BYTES=50)
    def test_tamano_excedido_400(self):
        f = SimpleUploadedFile(
            "big.jpg",
            b"x" * 200,
            content_type="image/jpeg",
        )
        r = self.client.post(
            f"/api/compras/expedientes/{self.eid}/documentos/",
            {"archivo": f},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data.get("codigo"), "tamano_excedido")

    def test_listar_y_detalle_documento(self):
        f = SimpleUploadedFile(
            "a.jpg",
            _mini_jpeg_bytes(),
            content_type="image/jpeg",
        )
        r0 = self.client.post(
            f"/api/compras/expedientes/{self.eid}/documentos/",
            {"archivo": f},
            format="multipart",
        )
        did = r0.data["id"]
        r1 = self.client.get(
            f"/api/compras/expedientes/{self.eid}/documentos/",
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r1.data), 1)
        r2 = self.client.get(
            f"/api/compras/expedientes/{self.eid}/documentos/{did}/",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertIn("resultado_ocr", r2.data)
