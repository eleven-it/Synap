from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.models import ExpedienteFacturaCompra
from factura_compra_captura.tests.compras_test_permissions import (
    otorgar_permisos_compras,
)
from factura_compra_posting.stub_adapter import FakeLegacyPostingAdapter
from factura_compra_captura.services.proveedor_legacy_service import ProveedorLegacyDTO


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

    def test_api_crear_expediente_sin_empresa_resuelve_desde_sesion(self):
        s = self.client.session
        s["empresa_activa_id"] = self.empresa.pk
        s.save()
        r = self.client.post(
            "/api/compras/expedientes/",
            {},
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

    @patch("factura_compra_captura.services.expediente_service.resolver_proveedor_desde_legacy_o_padron")
    def test_get_expediente_rellena_codigo_legacy_automatico_si_hay_cuit(self, mock_resolver):
        mock_resolver.return_value = type(
            "R",
            (),
            {
                "detail": "Proveedor encontrado en AdministraNET.",
                "codigo_proveedor_legacy": 456,
                "proveedor_synap": {
                    "modo": "legacy_vinculado",
                    "cuit": "30711222333",
                    "razon_social": "Auto SA",
                    "origen": "administranet",
                },
            },
        )()
        with override_settings(
            FACTURA_COMPRA_POSTING_BACKEND="fake",
            FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID={self.empresa.pk: "test_base"},
        ):
            r = self.client.post(
                "/api/compras/expedientes/",
                {
                    "empresa": self.empresa.pk,
                    "metadata": {
                        "proveedor_synap": {
                            "cuit": "30-71122233-3",
                            "razon_social": "Auto SA",
                        }
                    },
                },
                format="json",
            )
            self.assertEqual(r.status_code, status.HTTP_201_CREATED)
            self.assertIsNone(r.data.get("codigo_proveedor_legacy"))
            eid = r.data["id"]
            d = self.client.get(f"/api/compras/expedientes/{eid}/", format="json")
        self.assertEqual(d.status_code, status.HTTP_200_OK)
        self.assertEqual(d.data["codigo_proveedor_legacy"], 456)
        self.assertEqual(d.data["metadata"]["proveedor_synap"]["modo"], "legacy_vinculado")
        mock_resolver.assert_called_once()

    @patch(
        "factura_compra_captura.api.views.ExpedienteService.asegurar_codigo_proveedor_desde_cuit_si_falta",
    )
    @patch("factura_compra_captura.api.views.resolver_proveedor_desde_legacy_o_padron")
    def test_api_resolver_proveedor_si_existe_en_legacy(self, mock_resolver, mock_asegurar):
        mock_asegurar.side_effect = lambda exp, req: exp
        with override_settings(
            FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID={self.empresa.pk: "test_base"},
        ):
            r = self.client.post(
                "/api/compras/expedientes/",
                {"empresa": self.empresa.pk},
                format="json",
            )
            eid = r.data["id"]
            mock_resolver.return_value = type("R", (), {
                "detail": "Proveedor encontrado en AdministraNET.",
                "codigo_proveedor_legacy": 321,
                "proveedor_synap": {
                    "modo": "legacy_vinculado",
                    "cuit": "30711222333",
                    "razon_social": "Proveedor Legacy SA",
                },
            })()
            rr = self.client.post(
                f"/api/compras/expedientes/{eid}/resolver-proveedor/",
                {"cuit": "30-71122233-3"},
                format="json",
            )
            self.assertEqual(rr.status_code, status.HTTP_200_OK)
            self.assertEqual(rr.data["codigo_proveedor_legacy"], 321)
            d = self.client.get(f"/api/compras/expedientes/{eid}/", format="json")
        self.assertEqual(d.data["codigo_proveedor_legacy"], 321)
        self.assertEqual(d.data["metadata"]["proveedor_synap"]["modo"], "legacy_vinculado")

    @patch(
        "factura_compra_captura.api.views.ExpedienteService.asegurar_codigo_proveedor_desde_cuit_si_falta",
    )
    @patch("factura_compra_captura.api.views.resolver_proveedor_desde_legacy_o_padron")
    def test_api_resolver_proveedor_fallback_padron(self, mock_resolver, mock_asegurar):
        mock_asegurar.side_effect = lambda exp, req: exp
        with override_settings(
            FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID={self.empresa.pk: "test_base"},
        ):
            r = self.client.post(
                "/api/compras/expedientes/",
                {"empresa": self.empresa.pk},
                format="json",
            )
            eid = r.data["id"]
            mock_resolver.return_value = type("R", (), {
                "detail": "Proveedor no existe en AdministraNET; se precargó borrador desde padrón AFIP.",
                "codigo_proveedor_legacy": None,
                "proveedor_synap": {
                    "modo": "borrador_nuevo",
                    "cuit": "30711222333",
                    "razon_social": "Padron Prueba SA",
                    "tipo_factura_sugerida": "FA",
                },
            })()
            rr = self.client.post(
                f"/api/compras/expedientes/{eid}/resolver-proveedor/",
                {"cuit": "30-71122233-3"},
                format="json",
            )
            self.assertEqual(rr.status_code, status.HTTP_200_OK)
            self.assertIsNone(rr.data["codigo_proveedor_legacy"])
            d = self.client.get(f"/api/compras/expedientes/{eid}/", format="json")
        self.assertEqual(d.data["metadata"]["proveedor_synap"]["modo"], "borrador_nuevo")
        self.assertEqual(d.data["metadata"]["proveedor_synap"]["tipo_factura_sugerida"], "FA")

    @patch("factura_compra_captura.services.expediente_service.crear_proveedor_desde_borrador")
    @patch("factura_compra_captura.services.expediente_service.buscar_proveedor_por_cuit")
    def test_aprobacion_crea_proveedor_si_no_existe(self, mock_buscar, mock_crear):
        mock_buscar.return_value = None
        mock_crear.return_value = ProveedorLegacyDTO(
            codigo=777,
            nombre="Proveedor Nuevo",
            cuit="30711222333",
        )
        r = self.client.post(
            "/api/compras/expedientes/",
            {
                "empresa": self.empresa.pk,
                "metadata": {"proveedor_synap": {"cuit": "30711222333", "razon_social": "Proveedor Nuevo"}},
            },
            format="json",
        )
        eid = r.data["id"]
        self.client.patch(
            f"/api/compras/expedientes/{eid}/",
            {
                "posting_header": {
                    "nro_comprobante_formateado": "FA-0001-00000009",
                    "importe_total": "1.00",
                    "fecha_comprobante": "2026-01-15",
                    "tipo_factura": "FA",
                },
                "lineas": [
                    {"orden": 1, "id_art_legacy": 1, "cantidad": "1", "precio_unitario": "1"}
                ],
            },
            format="json",
        )
        ExpedienteFacturaCompra.objects.filter(pk=eid).update(
            estado=ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA
        )
        rr = self.client.post(
            f"/api/compras/expedientes/{eid}/aprobar/",
            {},
            format="json",
        )
        self.assertEqual(rr.status_code, status.HTTP_200_OK)
        self.assertEqual(rr.data["codigo_proveedor_legacy"], 777)
