"""UT-CMD-* — validación LegacyPostingCommandV1 (sin MySQL)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from factura_compra_posting.legacy_posting_command_v1 import (
    LegacyPostingCommandV1,
    PostingContextV1,
    PostingHeaderV1,
    PostingValidationError,
    StockLineCommandV1,
    validate_posting_command,
)


def _cmd_min(**kwargs):
    base = dict(
        idempotency_key="x:1",
        expediente_id=uuid4(),
        synap_empresa_id=1,
        context=PostingContextV1(
            id_usuario_legacy=1,
            id_vendedor_usuario=1,
            cod_sucursal=1,
            fecha_servidor=date.today(),
        ),
        header=PostingHeaderV1(
            codigo_proveedor=10,
            fecha_comprobante=date.today(),
            importe_total=Decimal("100.00"),
            nro_comprobante_formateado="FA-0001-00000001",
            tipo_factura="FA",
            tipo_factura_cabecera="Factura",
            origen="MANUAL",
            id_cond_compra=1,
            cond_compra_dias="0",
        ),
        lines=(
            StockLineCommandV1(
                orden=1,
                id_art=1,
                cantidad=Decimal("1"),
            ),
        ),
    )
    base.update(kwargs)
    return LegacyPostingCommandV1(**base)


class ValidatePostingCommandTests(SimpleTestCase):
    def test_ut_cmd_01_lineas_vacias(self):
        c = _cmd_min(lines=())
        with self.assertRaises(PostingValidationError) as ctx:
            validate_posting_command(c)
        self.assertEqual(ctx.exception.code, "V-01")

    def test_ut_cmd_02_importe_cero(self):
        c = _cmd_min(
            header=PostingHeaderV1(
                codigo_proveedor=1,
                fecha_comprobante=date.today(),
                importe_total=Decimal("0"),
                nro_comprobante_formateado="FA-1-1",
                tipo_factura="FA",
                tipo_factura_cabecera="Factura",
                origen="MANUAL",
                id_cond_compra=1,
                cond_compra_dias="0",
            ),
        )
        with self.assertRaises(PostingValidationError) as ctx:
            validate_posting_command(c)
        self.assertEqual(ctx.exception.code, "V-02")

    def test_ut_cmd_04_remito_sin_codmov(self):
        c = _cmd_min(
            header=PostingHeaderV1(
                codigo_proveedor=1,
                fecha_comprobante=date.today(),
                importe_total=Decimal("10"),
                nro_comprobante_formateado="FA-1-1",
                tipo_factura="FA",
                tipo_factura_cabecera="Factura Remito",
                origen="REMITO",
                id_cond_compra=1,
                cond_compra_dias="30",
            ),
            lines=(
                StockLineCommandV1(
                    orden=1,
                    id_art=1,
                    cantidad=Decimal("1"),
                    codigo_movimiento_remito=None,
                ),
            ),
        )
        with self.assertRaises(PostingValidationError) as ctx:
            validate_posting_command(c)
        self.assertEqual(ctx.exception.code, "V-04")

    def test_ut_cmd_09_lote_sin_codigo(self):
        c = _cmd_min(
            lines=(
                StockLineCommandV1(
                    orden=1,
                    id_art=1,
                    cantidad=Decimal("1"),
                    requiere_lote=True,
                    cod_lote=None,
                ),
            ),
        )
        with self.assertRaises(PostingValidationError) as ctx:
            validate_posting_command(c)
        self.assertEqual(ctx.exception.code, "V-09")
