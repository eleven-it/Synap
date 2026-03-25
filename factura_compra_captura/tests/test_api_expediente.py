from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.models import ExpedienteFacturaCompra
from factura_compra_captura.tests.compras_test_permissions import (
    otorgar_permisos_compras,
)
from factura_compra_posting.stub_adapter import FakeLegacyPostingAdapter


@override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
class ExpedienteAPITests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="API FC Test",
            razon_social="API FC Test SA",
            identificador_fiscal="20987654321",
        )
        self.user = UsuarioExtendido.objects.create_user(
            email="api-fc@test.local",
            nombre="API User",
            password="secret123",
        )
        self.user.uid = "test-uid-api-fc"
        self.user.save()
        otorgar_permisos_compras(self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_api_crear_expediente_201(self):
        r = self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["estado"], ExpedienteFacturaCompra.Estado.BORRADOR)
        self.assertEqual(r.data["empresa"], self.empresa.pk)

    def test_api_listar_filtrado_por_estado(self):
        self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        r = self.client.get(
            "/api/compras/expedientes/",
            {"estado": "borrador", "empresa": self.empresa.pk},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(r.data), 1)

    def test_api_patch_y_transicion_flujo(self):
        r = self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        eid = r.data["id"]
        r2 = self.client.patch(
            f"/api/compras/expedientes/{eid}/",
            {
                "codigo_proveedor_legacy": 2002,
                "lineas": [
                    {
                        "orden": 1,
                        "id_art_legacy": 99,
                        "cantidad": "2",
                        "precio_unitario": "15.50",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        r3 = self.client.post(
            f"/api/compras/expedientes/{eid}/transiciones/",
            {"accion": "enviar_revision"},
            format="json",
        )
        self.assertEqual(r3.status_code, status.HTTP_200_OK)
        self.assertEqual(r3.data["estado"], ExpedienteFacturaCompra.Estado.EN_REVISION)

    def test_api_transicion_simular_posting_setea_legacy_fake(self):
        r = self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        eid = r.data["id"]
        self.client.patch(
            f"/api/compras/expedientes/{eid}/",
            {
                "codigo_proveedor_legacy": 1,
                "posting_header": {
                    "nro_comprobante_formateado": "FA-0001-00000001",
                    "importe_total": "1.00",
                    "fecha_comprobante": "2026-01-15",
                    "tipo_factura": "FA",
                },
                "lineas": [
                    {
                        "orden": 1,
                        "id_art_legacy": 1,
                        "cantidad": "1",
                        "precio_unitario": "1",
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
            {"accion": "solicitar_aprobacion"},
            format="json",
        )
        r_final = self.client.post(
            f"/api/compras/expedientes/{eid}/transiciones/",
            {"accion": "simular_posting_exitoso"},
            format="json",
        )
        self.assertEqual(r_final.status_code, status.HTTP_200_OK)
        self.assertEqual(r_final.data["estado"], ExpedienteFacturaCompra.Estado.APROBADO)
        self.assertEqual(
            r_final.data["legacy_codigo_movimiento"],
            FakeLegacyPostingAdapter.FAKE_CODMOV,
        )

    def test_api_get_eventos_historial(self):
        r = self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        eid = r.data["id"]
        r_ev = self.client.get(f"/api/compras/expedientes/{eid}/eventos/")
        self.assertEqual(r_ev.status_code, status.HTTP_200_OK)
        self.assertIsInstance(r_ev.data, list)
        self.assertTrue(any(e["tipo_evento"] == "expediente_creado" for e in r_ev.data))
