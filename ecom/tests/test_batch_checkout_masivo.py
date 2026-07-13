"""Tests Phase 5 — batch checkout masivo + compensación."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.batch_checkout_masivo import confirmar_lote_masivo


class TestConfirmarLoteMasivo(TestCase):
    def _draft_con_dos_sucursales(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b",
            id_usuario=9,
            id_cliente=100,
            cod_viajante=2,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d, id_articulo=1, id_cliente_domicilio=10, cantidad_packs=Decimal("2")
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d, id_articulo=1, id_cliente_domicilio=20, cantidad_packs=Decimal("3")
        )
        return d

    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_ok_dos_ped(self, mock_conf, mock_add, mock_opts):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 101, "nro_comprobante": "A-1"}),
            (True, None, {"codigo_movimiento": 102, "nro_comprobante": "A-2"}),
        ]
        d = self._draft_con_dos_sucursales()
        ok, msg, payload = confirmar_lote_masivo(
            d, id_usuario=9, id_punto_venta=1, cod_viajante=2
        )
        self.assertTrue(ok)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_CONFIRMADO)
        self.assertEqual(d.codigos_movimiento, [101, 102])
        self.assertEqual(mock_conf.call_count, 2)
        # id_cliente_domicilio en cada checkout
        doms = [
            mock_conf.call_args_list[i].args[1].id_cliente_domicilio for i in range(2)
        ]
        self.assertEqual(sorted(doms), [10, 20])

    @patch("ecom.services.batch_checkout_masivo.anular_pedido_relay")
    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_fail_segunda_compensa_primera(self, mock_conf, mock_add, mock_opts, mock_anular):
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.side_effect = [
            (True, None, {"codigo_movimiento": 201}),
            (False, "Stock insuficiente", None),
        ]
        mock_anular.return_value = {"msg": "ok", "error": ""}
        d = self._draft_con_dos_sucursales()
        # celdas count before
        n_celdas = d.celdas.count()
        ok, msg, payload = confirmar_lote_masivo(
            d, id_usuario=9, id_punto_venta=1, cod_viajante=2
        )
        self.assertFalse(ok)
        self.assertIn("Stock", msg)
        mock_anular.assert_called_once()
        self.assertEqual(mock_anular.call_args.args[1], 201)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_BORRADOR)
        self.assertEqual(d.codigos_movimiento, [])
        self.assertIn("20", d.ultimo_error)
        self.assertEqual(d.celdas.count(), n_celdas)

    def test_sin_cantidades(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_b", id_usuario=1, id_cliente=1
        )
        ok, msg, _ = confirmar_lote_masivo(d, id_usuario=1, id_punto_venta=1)
        self.assertFalse(ok)
        self.assertIn("cantidades", msg.lower())
