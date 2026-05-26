"""
PASO 3 (TDD) — validación duplicados y fiscal antes de aprobar.

Especificación: docs/compras/change_design.md

Ejecutar: python manage.py test tests.compras.test_validation_phase3_5

PASO 4: servicios e integración en `aprobar_expediente_con_stub` implementados; la suite
debe pasar en verde. Flujos con CAE en tests pasan `base_empresa` explícito; en API web
se usa `request` + sesión (`user.base_empresa`) o `metadata["compras"]["base_empresa"]`
o `settings.FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID`.
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings

from core.models import Empresa
from factura_compra_captura.models import ExpedienteFacturaCompra
from factura_compra_captura.services import ExpedienteService, TransicionEstadoInvalida
from factura_compra_captura.services.duplicate_detection import (
    DuplicateCheckResult,
    DuplicateCheckStatus,
    DuplicateDetectionService,
)
from factura_compra_captura.services.fiscal_invoice_validation import (
    FiscalInvoiceValidationService,
    FiscalValidationResult,
    FiscalValidationStatus,
)
from factura_compra_posting.mapper_v1 import map_expediente_to_command_v1


def _call_duplicate_or_fail(testcase: TestCase, *args, **kwargs) -> DuplicateCheckResult:
    try:
        return DuplicateDetectionService.check_for_approval(*args, **kwargs)
    except NotImplementedError as e:
        testcase.fail(
            "Pendiente PASO 4: implementar DuplicateDetectionService.check_for_approval. "
            f"({e})"
        )


def _call_fiscal_or_fail(testcase: TestCase, *args, **kwargs) -> FiscalValidationResult:
    try:
        return FiscalInvoiceValidationService.validate_for_approval(*args, **kwargs)
    except NotImplementedError as e:
        testcase.fail(
            "Pendiente PASO 4: implementar FiscalInvoiceValidationService.validate_for_approval. "
            f"({e})"
        )


@override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
class DuplicateDetectionServiceTests(TestCase):
    """Contrato DuplicateDetectionService — diseño §2.1 y §2.2."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa TDD Compras Val",
            razon_social="Empresa TDD Compras Val SA",
            identificador_fiscal="20987654321",
        )

    def _expediente_en_aprobacion(
        self,
        *,
        codigo_proveedor_legacy: int = 4400,
        nro_comprobante_formateado: str = "FA-0001-00000100",
        estado_destino: str = ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA,
    ) -> ExpedienteFacturaCompra:
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=codigo_proveedor_legacy,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 101,
                    "cantidad": "1",
                    "precio_unitario": "100.00",
                }
            ],
            posting_header={
                "nro_comprobante_formateado": nro_comprobante_formateado,
                "importe_total": "100.00",
                "fecha_comprobante": "2026-03-01",
                "tipo_factura": "FA",
            },
        )
        exp.refresh_from_db()
        exp = ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        exp = ExpedienteService.aplicar_transicion(exp, "marcar_listo_para_aprobar")
        exp = ExpedienteService.aplicar_transicion(exp, "solicitar_aprobacion")
        self.assertEqual(exp.estado, estado_destino)
        return exp

    def _cmd(self, exp: ExpedienteFacturaCompra):
        return map_expediente_to_command_v1(exp, idempotency_key=f"{exp.id}:1")

    def test_mismo_expediente_excluido_no_es_duplicado(self):
        """
        Al aprobar, el propio expediente no debe contarse como colisión (exclude id).
        Esperado tras PASO 4: CLEAR, blocking False.
        """
        exp = self._expediente_en_aprobacion()
        cmd = self._cmd(exp)
        r = _call_duplicate_or_fail(self, exp, cmd, exclude_expediente_id=exp.id)
        self.assertEqual(r.status, DuplicateCheckStatus.CLEAR)
        self.assertFalse(r.blocking)

    def test_mismo_proveedor_y_numero_otro_expediente_es_duplicado(self):
        """
        Dos expedientes misma empresa, mismo codigo_proveedor_legacy y mismo comprobante
        normalizado → BLOCKED.
        """
        exp_a = self._expediente_en_aprobacion(
            nro_comprobante_formateado="FA-0001-00000200",
        )
        ExpedienteService.aprobar_expediente_con_stub(exp_a)
        exp_a.refresh_from_db()
        self.assertEqual(exp_a.estado, ExpedienteFacturaCompra.Estado.APROBADO)

        exp_b = self._expediente_en_aprobacion(
            nro_comprobante_formateado="FA-0001-00000200",
        )
        cmd_b = self._cmd(exp_b)
        r = _call_duplicate_or_fail(self, exp_b, cmd_b)
        self.assertEqual(r.status, DuplicateCheckStatus.BLOCKED)
        self.assertTrue(r.blocking)
        self.assertTrue(
            any("duplicate_factura" in rc for rc in r.reason_codes),
            msg=f"Se esperaba un reason_code con prefijo/infix duplicate_factura: {r.reason_codes!r}",
        )

    def test_formato_distinto_mismo_comprobante_detectado_como_duplicado(self):
        """
        Variantes de formato (p. ej. mayúsculas/minúsculas, espacios) deben
        normalizarse a la misma clave §2.2 → BLOCKED frente a expediente ya aprobado.
        """
        exp_a = self._expediente_en_aprobacion(
            nro_comprobante_formateado="FA-0001-00000333",
        )
        ExpedienteService.aprobar_expediente_con_stub(exp_a)

        exp_b = self._expediente_en_aprobacion(
            nro_comprobante_formateado="fa-0001-00000333",
        )
        cmd_b = self._cmd(exp_b)
        r = _call_duplicate_or_fail(self, exp_b, cmd_b)
        self.assertEqual(r.status, DuplicateCheckStatus.BLOCKED)
        self.assertTrue(r.blocking)
        self.assertTrue(
            any("duplicate_factura" in rc for rc in r.reason_codes),
            msg=r.reason_codes,
        )

    def test_normalizacion_con_espacios(self):
        """
        Espacios laterales en nro_comprobante_formateado no deben evitar el match
        con el comprobante ya aprobado (misma clave normalizada §2.2).
        """
        exp_a = self._expediente_en_aprobacion(
            nro_comprobante_formateado="FA-0001-00000444",
        )
        ExpedienteService.aprobar_expediente_con_stub(exp_a)

        exp_b = self._expediente_en_aprobacion(
            nro_comprobante_formateado=" FA-0001-00000444 ",
        )
        cmd_b = self._cmd(exp_b)
        r = _call_duplicate_or_fail(self, exp_b, cmd_b)
        self.assertEqual(r.status, DuplicateCheckStatus.BLOCKED)
        self.assertTrue(r.blocking)
        self.assertTrue(
            any("duplicate_factura" in rc for rc in r.reason_codes),
            msg=r.reason_codes,
        )


@override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
class FiscalInvoiceValidationServiceTests(TestCase):
    """Contrato FiscalInvoiceValidationService — diseño §5.3 y §4.5."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa TDD Fiscal",
            razon_social="Empresa TDD Fiscal SA",
            identificador_fiscal="20334445556",
        )

    def _expediente_con_header(
        self,
        *,
        posting_header_extra: dict | None = None,
    ) -> ExpedienteFacturaCompra:
        header = {
            "nro_comprobante_formateado": "FB-0002-00000055",
            "importe_total": "50.00",
            "fecha_comprobante": "2026-03-10",
            "tipo_factura": "FB",
        }
        if posting_header_extra:
            header.update(posting_header_extra)
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=5500,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 202,
                    "cantidad": "1",
                    "precio_unitario": "50.00",
                }
            ],
            posting_header=header,
        )
        exp.refresh_from_db()
        exp = ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        exp = ExpedienteService.aplicar_transicion(exp, "marcar_listo_para_aprobar")
        exp = ExpedienteService.aplicar_transicion(exp, "solicitar_aprobacion")
        return exp

    def test_cae_valido_afip_coincide_ok(self):
        exp = self._expediente_con_header(
            posting_header_extra={
                "cae": "12345678901234",
                "pto_vta_afip": 2,
                "nro_cbte_afip": 55,
            },
        )
        cmd = map_expediente_to_command_v1(exp, idempotency_key=f"{exp.id}:1")
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=("12345678901234", "20260320", None),
        ):
            r = _call_fiscal_or_fail(
                self, exp, cmd, base_empresa="base_test_fe"
            )
        self.assertEqual(r.status, FiscalValidationStatus.VALID)
        self.assertFalse(r.blocking)

    def test_cae_no_existe_en_afip_invalid(self):
        exp = self._expediente_con_header(
            posting_header_extra={
                "cae": "99999999999999",
                "pto_vta_afip": 2,
                "nro_cbte_afip": 99,
            },
        )
        cmd = map_expediente_to_command_v1(exp, idempotency_key=f"{exp.id}:1")
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=(None, None, "Comprobante no encontrado"),
        ):
            r = _call_fiscal_or_fail(
                self, exp, cmd, base_empresa="base_test_fe"
            )
        self.assertEqual(r.status, FiscalValidationStatus.INVALID)
        self.assertTrue(r.blocking)

    def test_afip_caida_error_transient_bloquea_modo_estricto(self):
        exp = self._expediente_con_header(
            posting_header_extra={
                "cae": "11111111111111",
                "pto_vta_afip": 3,
                "nro_cbte_afip": 1,
            },
        )
        cmd = map_expediente_to_command_v1(exp, idempotency_key=f"{exp.id}:1")
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=(None, None, "timeout/red"),
        ):
            r = _call_fiscal_or_fail(
                self, exp, cmd, base_empresa="base_test_fe"
            )
        self.assertEqual(r.status, FiscalValidationStatus.ERROR_TRANSIENT)
        self.assertTrue(r.blocking)

    def test_afip_no_configurado_codigo_not_configured(self):
        exp = self._expediente_con_header(
            posting_header_extra={
                "cae": "11111111111111",
                "pto_vta_afip": 3,
                "nro_cbte_afip": 1,
            },
        )
        cmd = map_expediente_to_command_v1(exp, idempotency_key=f"{exp.id}:1")
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=(None, None, "AFIP no configurado para esta base"),
        ):
            r = _call_fiscal_or_fail(
                self, exp, cmd, base_empresa="base_test_fe"
            )
        self.assertEqual(r.status, FiscalValidationStatus.INVALID)
        self.assertTrue(r.blocking)
        self.assertIn("fiscal_afip_not_configured", r.reason_codes)

    def test_fm_no_consulta_wsfe(self):
        exp = self._expediente_con_header(
            posting_header_extra={
                "cae": "22222222222222",
                "pto_vta_afip": 1,
                "nro_cbte_afip": 77,
                "tipo_factura": "FM",
            },
        )
        cmd = map_expediente_to_command_v1(exp, idempotency_key=f"{exp.id}:1")
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
        ) as m:
            r = _call_fiscal_or_fail(
                self, exp, cmd, base_empresa="base_test_fe"
            )
            m.assert_not_called()
        self.assertEqual(r.status, FiscalValidationStatus.SKIPPED_NON_AR)
        self.assertFalse(r.blocking)
        self.assertIn("fiscal_skip_tipo_fm", r.reason_codes)


@override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
class AprobarExpedienteValidacionFlujoTests(TestCase):
    """Integración prevista en aprobar_expediente_con_stub (diseño §3)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa TDD Flujo",
            razon_social="Empresa TDD Flujo SA",
            identificador_fiscal="20556667778",
        )

    def _expediente_aprobacion(
        self, nro: str, proveedor: int = 6600
    ) -> ExpedienteFacturaCompra:
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=proveedor,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 303,
                    "cantidad": "1",
                    "precio_unitario": "10.00",
                }
            ],
            posting_header={
                "nro_comprobante_formateado": nro,
                "importe_total": "10.00",
                "fecha_comprobante": "2026-03-15",
                "tipo_factura": "FA",
            },
        )
        exp.refresh_from_db()
        exp = ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        exp = ExpedienteService.aplicar_transicion(exp, "marcar_listo_para_aprobar")
        exp = ExpedienteService.aplicar_transicion(exp, "solicitar_aprobacion")
        return exp

    def test_flujo_duplicado_bloquea_aprobacion(self):
        a = self._expediente_aprobacion("FA-0001-00000999")
        ExpedienteService.aprobar_expediente_con_stub(a)
        b = self._expediente_aprobacion("FA-0001-00000999")
        with self.assertRaises(TransicionEstadoInvalida) as ctx:
            ExpedienteService.aprobar_expediente_con_stub(b)
        self.assertIn(
            ctx.exception.codigo,
            ("duplicate_factura_synap", "duplicate_factura_legacy"),
        )

    def test_flujo_fiscal_invalido_bloquea_aprobacion(self):
        exp = self._expediente_aprobacion("FA-0001-00000888")
        md = dict(exp.metadata or {})
        pv = dict(md.get("posting_v1") or {})
        h = dict(pv.get("header") or {})
        h.update(
            {
                "cae": "77777777777777",
                "pto_vta_afip": 1,
                "nro_cbte_afip": 888,
            }
        )
        pv["header"] = h
        md["posting_v1"] = pv
        exp.metadata = md
        exp.save(update_fields=["metadata"])
        exp.refresh_from_db()
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=(None, None, "no existe"),
        ):
            with self.assertRaises(TransicionEstadoInvalida) as ctx:
                ExpedienteService.aprobar_expediente_con_stub(
                    exp, base_empresa="base_tdd_fiscal"
                )
        self.assertIn(
            ctx.exception.codigo,
            (
                "fiscal_afip_invalid",
                "fiscal_afip_unavailable",
                "fiscal_afip_not_configured",
            ),
        )

    def test_flujo_afip_caido_bloquea(self):
        """
        Modo estricto: con CAE declarado, fallo transitorio AFIP → bloqueo en aprobación.
        Requiere metadata fiscal (misma convención que test_flujo_fiscal_invalido).
        """
        exp = self._expediente_aprobacion("FA-0001-00000666")
        md = dict(exp.metadata or {})
        pv = dict(md.get("posting_v1") or {})
        h = dict(pv.get("header") or {})
        h.update(
            {
                "cae": "66666666666666",
                "pto_vta_afip": 1,
                "nro_cbte_afip": 666,
            }
        )
        pv["header"] = h
        md["posting_v1"] = pv
        exp.metadata = md
        exp.save(update_fields=["metadata"])
        exp.refresh_from_db()
        with patch(
            "self_checkout.fe_sync.consultar_cae_comprobante",
            return_value=(None, None, "timeout"),
        ):
            with self.assertRaises(TransicionEstadoInvalida) as ctx:
                ExpedienteService.aprobar_expediente_con_stub(
                    exp, base_empresa="base_tdd_fiscal"
                )
        self.assertEqual(ctx.exception.codigo, "fiscal_afip_unavailable")

    def test_flujo_sin_cae_no_bloquea(self):
        """
        Sin CAE en cabecera/metadata: no se exige consulta AFIP (§5.3) → debe aprobar
        con stub como hoy.
        """
        exp = self._expediente_aprobacion("FA-0001-00000555")
        out = ExpedienteService.aprobar_expediente_con_stub(exp)
        self.assertEqual(out.estado, ExpedienteFacturaCompra.Estado.APROBADO)

    def test_flujo_valido_permite_aprobacion(self):
        exp = self._expediente_aprobacion("FA-0001-00000777")
        out = ExpedienteService.aprobar_expediente_con_stub(exp)
        self.assertEqual(out.estado, ExpedienteFacturaCompra.Estado.APROBADO)
