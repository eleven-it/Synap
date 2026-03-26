from django.test import TestCase, override_settings

from core.models import Empresa
from factura_compra_captura.models import ExpedienteFacturaCompra
from factura_compra_captura.services import ExpedienteService, TransicionEstadoInvalida
from factura_compra_captura.services.transiciones_estado import listar_acciones_permitidas


class TransicionesExpedienteTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test FC",
            razon_social="Empresa Test FC SA",
            identificador_fiscal="20123456780",
        )

    def test_borrador_a_ocr_completado(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        exp = ExpedienteService.aplicar_transicion(exp, "marcar_ocr_completado")
        self.assertEqual(exp.estado, ExpedienteFacturaCompra.Estado.OCR_COMPLETADO)

    def test_transicion_borrador_a_en_revision_requiere_datos_minimos(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        with self.assertRaises(TransicionEstadoInvalida) as ctx:
            ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        self.assertEqual(ctx.exception.codigo, "proveedor_requerido")

        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=1001,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 55,
                    "cantidad": "1",
                    "precio_unitario": "10.00",
                }
            ],
        )
        exp.refresh_from_db()
        exp = ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        self.assertEqual(exp.estado, ExpedienteFacturaCompra.Estado.EN_REVISION)

    def test_transicion_invalida_lanza_error(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        with self.assertRaises(TransicionEstadoInvalida) as ctx:
            ExpedienteService.aplicar_transicion(exp, "solicitar_aprobacion")
        self.assertEqual(ctx.exception.codigo, "transicion_invalida")

    def test_rechazar_requiere_motivo(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=1,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 1,
                    "cantidad": "1",
                    "precio_unitario": "1",
                }
            ],
        )
        exp.refresh_from_db()
        exp = ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        with self.assertRaises(TransicionEstadoInvalida):
            ExpedienteService.aplicar_transicion(exp, "rechazar", payload={})
        exp = ExpedienteService.aplicar_transicion(
            exp, "rechazar", payload={"motivo": "  Datos incorrectos  "}
        )
        self.assertEqual(exp.estado, ExpedienteFacturaCompra.Estado.RECHAZADO)
        self.assertIn("incorrectos", exp.rechazo_motivo)

    def test_listar_acciones_permitidas_borrador(self):
        acc = listar_acciones_permitidas(ExpedienteFacturaCompra.Estado.BORRADOR)
        self.assertIn("marcar_ocr_completado", acc)
        self.assertIn("enviar_revision", acc)

    def test_linea_cantidad_cero_falla_enviar_revision(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=1,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 1,
                    "cantidad": "0",
                    "precio_unitario": "1",
                }
            ],
        )
        exp.refresh_from_db()
        with self.assertRaises(TransicionEstadoInvalida) as ctx:
            ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        self.assertEqual(ctx.exception.codigo, "linea_cantidad_invalida")

    def test_enviar_revision_falla_sin_id_art_legacy(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=1,
            lineas=[
                {
                    "orden": 1,
                    "cantidad": "1",
                    "precio_unitario": "100.00",
                }
            ],
        )
        exp.refresh_from_db()
        with self.assertRaises(TransicionEstadoInvalida) as ctx:
            ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        self.assertEqual(ctx.exception.codigo, "linea_sin_articulo")

    @override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
    def test_aprobar_stub_requiere_nro_comprobante_en_metadata(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=1,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 1,
                    "cantidad": "1",
                    "precio_unitario": "1",
                }
            ],
        )
        exp.refresh_from_db()
        exp = ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        exp = ExpedienteService.aplicar_transicion(exp, "marcar_listo_para_aprobar")
        exp = ExpedienteService.aplicar_transicion(exp, "solicitar_aprobacion")
        with self.assertRaises(TransicionEstadoInvalida) as ctx:
            ExpedienteService.aprobar_expediente_con_stub(exp)
        self.assertEqual(ctx.exception.codigo, "V-HDR-NRO")

    @override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
    def test_aprobar_stub_ok_con_posting_header(self):
        exp = ExpedienteService.crear(empresa_id=self.empresa.pk)
        ExpedienteService.actualizar(
            exp,
            codigo_proveedor_legacy=1,
            lineas=[
                {
                    "orden": 1,
                    "id_art_legacy": 1,
                    "cantidad": "1",
                    "precio_unitario": "1",
                }
            ],
            posting_header={
                "nro_comprobante_formateado": "FA-0001-00000099",
                "importe_total": "1.00",
                "fecha_comprobante": "2026-02-01",
            },
        )
        exp.refresh_from_db()
        exp = ExpedienteService.aplicar_transicion(exp, "enviar_revision")
        exp = ExpedienteService.aplicar_transicion(exp, "marcar_listo_para_aprobar")
        exp = ExpedienteService.aplicar_transicion(exp, "solicitar_aprobacion")
        exp = ExpedienteService.aprobar_expediente_con_stub(exp)
        self.assertEqual(exp.estado, ExpedienteFacturaCompra.Estado.APROBADO)
