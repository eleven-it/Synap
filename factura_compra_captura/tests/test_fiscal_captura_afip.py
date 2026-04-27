"""Verificación fiscal AFIP en captura (advisory) y utilidades asociadas."""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.models import ExpedienteFacturaCompra
from factura_compra_captura.services import ExpedienteService
from factura_compra_captura.services.fiscal_invoice_validation import (
    FiscalInvoiceValidationService,
    FiscalValidationStatus,
    infer_pto_vta_y_nro_cbte_desde_formateado,
)
from factura_compra_captura.tests.compras_test_permissions import (
    otorgar_permisos_compras,
)
from factura_compra_posting.mapper_v1 import map_expediente_to_command_v1


class InferPtoNroAfipTests(TestCase):
    def test_infer_desde_fa_formateado(self):
        self.assertEqual(infer_pto_vta_y_nro_cbte_desde_formateado("FA-0001-00000100"), (1, 100))

    def test_infer_barra(self):
        self.assertEqual(infer_pto_vta_y_nro_cbte_desde_formateado("FB-0002/00000055"), (2, 55))

    def test_vacio(self):
        self.assertEqual(infer_pto_vta_y_nro_cbte_desde_formateado(""), (None, None))


@override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
class ValidateForCapturaTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Emp Captura AFIP",
            razon_social="Emp Captura AFIP SA",
            identificador_fiscal="20999888776",
        )

    def test_captura_timeout_no_bloquea(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=9001,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 1,
                    "cantidad": "1",
                    "precio_unitario": "10.00",
                }
            ],
            posting_header={
                "nro_comprobante_formateado": "FA-0003-00000007",
                "importe_total": "10.00",
                "fecha_comprobante": "2026-03-01",
                "tipo_factura": "FA",
                "cae": "11111111111111",
                "pto_vta_afip": 3,
                "nro_cbte_afip": 7,
            },
        )
        exp.refresh_from_db()
        cmd = map_expediente_to_command_v1(exp, idempotency_key=f"{exp.id}:1")
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=(None, None, "timeout de red"),
        ):
            r = FiscalInvoiceValidationService.validate_for_captura(
                exp, cmd, base_empresa="base_x"
            )
        self.assertEqual(r.status, FiscalValidationStatus.ERROR_TRANSIENT)
        self.assertFalse(r.blocking)


@override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
class FiscalCapturaAPIPersistenceTests(TestCase):
    """PATCH con request persiste metadata de verificación (mock AFIP)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Emp API Fiscal",
            razon_social="Emp API Fiscal SA",
            identificador_fiscal="20988776655",
        )
        self.user = UsuarioExtendido.objects.create_user(
            email="fiscal-cap@test.local",
            nombre="Fiscal Cap",
            password="secret123",
        )
        self.user.uid = "uid-fiscal-cap"
        self.user.save()
        otorgar_permisos_compras(self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_patch_posting_header_guarda_verificacion_afip_en_metadata(self):
        r = self.client.post(
            "/api/compras/expedientes/",
            {"empresa": self.empresa.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        eid = r.data["id"]
        mapping = {self.empresa.pk: "base_fe_captura_test"}
        with override_settings(FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID=mapping), patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=("12345678901234", "20260320", None),
        ):
            r2 = self.client.patch(
                f"/api/compras/expedientes/{eid}/",
                {
                    "codigo_proveedor_legacy": 8001,
                    "lineas": [
                        {
                            "orden": 1,
                            "id_art_legacy": 42,
                            "cantidad": "1",
                            "precio_unitario": "100.00",
                        }
                    ],
                    "posting_header": {
                        "nro_comprobante_formateado": "FA-0005-00000088",
                        "importe_total": "100.00",
                        "fecha_comprobante": "2026-04-01",
                        "tipo_factura": "FA",
                        "cae": "12345678901234",
                        "pto_vta_afip": 5,
                        "nro_cbte_afip": 88,
                    },
                },
                format="json",
            )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        snap = r2.data.get("fiscal_afip_verificacion_captura")
        self.assertIsInstance(snap, dict)
        self.assertEqual(snap.get("status"), "valid")
        exp = ExpedienteFacturaCompra.objects.get(pk=eid)
        md = exp.metadata or {}
        compras = md.get("compras") or {}
        self.assertEqual((compras.get("fiscal_afip_verificacion_captura") or {}).get("status"), "valid")
