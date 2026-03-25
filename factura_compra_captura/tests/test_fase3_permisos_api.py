"""Permisos API Fase 3 (product_requirements §10)."""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.models import ExpedienteFacturaCompra


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
