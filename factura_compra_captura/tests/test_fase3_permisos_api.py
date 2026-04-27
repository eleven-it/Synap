"""Permisos API Fase 3 (product_requirements §10)."""

from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.api import views as compras_api_views
from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
from factura_compra_captura.tests.compras_test_permissions import otorgar_permisos_compras
from factura_compra_captura.tests.test_documento_upload import _mini_jpeg_bytes


@override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
class AprobarSinPermisoTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Perm FC",
            razon_social="Perm FC SA",
            identificador_fiscal="20999888777",
        )
        self.user = UsuarioExtendido.objects.create_user(
            email="perm-fc@test.local",
            nombre="Perm",
            password="x",
        )
        self.user.is_superuser = False
        self.user.save()
        ct = ContentType.objects.get_for_model(ExpedienteFacturaCompra)
        for codename in ("ver", "crear", "editar", "revisar"):
            p = Permission.objects.get(content_type=ct, codename=codename)
            self.user.user_permissions.add(p)
        if hasattr(self.user, "_perm_cache"):
            self.user._perm_cache = {}
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_post_aprobar_403_sin_permiso_aprobar(self):
        r0 = self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        eid = r0.data["id"]
        self.client.patch(
            f"/api/compras/expedientes/{eid}/",
            {
                "codigo_proveedor_legacy": 1,
                "posting_header": {
                    "nro_comprobante_formateado": "FA-0001-00000001",
                    "importe_total": "10",
                    "fecha_comprobante": "2026-01-10",
                },
                "lineas": [
                    {
                        "orden": 1,
                        "id_art_legacy": 1,
                        "cantidad": "1",
                        "precio_unitario": "10",
                    }
                ],
            },
            format="json",
        )
        self.client.post(
            f"/api/compras/expedientes/{eid}/transiciones/",
            {"accion": "enviar_revision"},
            format="json",
        )
        self.client.post(
            f"/api/compras/expedientes/{eid}/transiciones/",
            {"accion": "marcar_listo_para_aprobar"},
            format="json",
        )
        self.client.post(
            f"/api/compras/expedientes/{eid}/transiciones/",
            {"accion": "solicitar_aprobacion"},
            format="json",
        )
        r = self.client.post(f"/api/compras/expedientes/{eid}/aprobar/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class _BoomOcrAdapter:
    def procesar(self, *_args, **_kwargs):
        raise RuntimeError("ocr fallo test")


@override_settings(
    FACTURA_COMPRA_OCR_SYNC=True,
    FACTURA_COMPRA_OCR_TESSERACT_ENABLED=False,
)
class ReintentarOcrRequiereEditarTests(TestCase):
    """Reintento OCR no debe quedar abierto a quien solo puede capturar (crear)."""

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
            nombre="Reint Perm",
            razon_social="Reint Perm SA",
            identificador_fiscal="20988776655",
        )
        self.user_setup = UsuarioExtendido.objects.create_user(
            email="reint-setup@test.local",
            nombre="Setup",
            password="x",
        )
        self.user_setup.uid = "uid-reint-setup"
        self.user_setup.save()
        otorgar_permisos_compras(self.user_setup)
        self.client_setup = APIClient()
        self.client_setup.force_authenticate(user=self.user_setup)
        with patch(
            "factura_compra_captura.ocr.pipeline.get_ocr_adapter",
            return_value=_BoomOcrAdapter(),
        ):
            f = SimpleUploadedFile(
                "f.jpg",
                _mini_jpeg_bytes(),
                content_type="image/jpeg",
            )
            r0 = self.client_setup.post(
                "/api/compras/expedientes/",
                {"empresa": self.empresa.pk},
                format="json",
            )
            self.eid = r0.data["id"]
            r1 = self.client_setup.post(
                f"/api/compras/expedientes/{self.eid}/documentos/",
                {"archivo": f},
                format="multipart",
            )
        self.did = r1.data["id"]
        self.assertEqual(
            DocumentoFuente.objects.get(pk=self.did).estado_procesamiento,
            DocumentoFuente.EstadoProcesamiento.FALLIDO,
        )

        self.user_solo_crear = UsuarioExtendido.objects.create_user(
            email="reint-solo-crear@test.local",
            nombre="Solo Crear",
            password="x",
        )
        ct = ContentType.objects.get_for_model(ExpedienteFacturaCompra)
        for codename in ("ver", "crear"):
            self.user_solo_crear.user_permissions.add(
                Permission.objects.get(content_type=ct, codename=codename)
            )
        if hasattr(self.user_solo_crear, "_perm_cache"):
            self.user_solo_crear._perm_cache = {}

    def test_reintentar_ocr_403_sin_editar_ni_reintentar_posting(self):
        client = APIClient()
        client.force_authenticate(user=self.user_solo_crear)
        r = client.post(
            f"/api/compras/expedientes/{self.eid}/documentos/{self.did}/reintentar-ocr/",
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
