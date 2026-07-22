"""Tests básicos — resumen de lote masivo (Phase 4)."""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.lote_resumen import LoteResumenError, construir_resumen_lote


def _sucursales_vcm_mock(ids=(10, 20)):
    return [{"id_cliente_domicilio": i, "nombre": f"Suc {i}"} for i in ids]


class TestLoteResumen(TestCase):
    def setUp(self):
        self.base = "test_base"
        self.sess = {"id_usuario": 7, "base_empresa": self.base, "tipousuario": "vendedor"}
        self.draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa=self.base,
            id_usuario=7,
            id_cliente=100,
            cod_viajante=5,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMADO,
            codigos_movimiento=[9001, 9002],
            estado_aprobacion_lote=EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_PENDIENTE,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=self.draft,
            id_articulo=1,
            id_cliente_domicilio=10,
            cantidad_packs=Decimal("2"),
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=self.draft,
            id_articulo=1,
            id_cliente_domicilio=20,
            cantidad_packs=Decimal("1"),
        )

    @patch("ecom.services.lote_resumen.listar_sucursales_cliente", return_value=_sucursales_vcm_mock())
    @patch("ecom.services.lote_resumen.puede_aprobar_lote", return_value=False)
    @patch("ecom.services.lote_resumen.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.lote_resumen._nombre_cliente", return_value="ACME SA")
    @patch("ecom.services.lote_resumen._mapa_nombres_sucursales")
    @patch("ecom.services.lote_resumen._fetch_pedidos_lote_detalle")
    @patch("ecom.services.lote_resumen._draft_en_alcance_hub", return_value=True)
    def test_payload_coherente(
        self,
        _mock_alcance,
        mock_fetch,
        mock_nombres,
        _mock_nombre_cli,
        _mock_aprob,
        _mock_puede,
        _mock_vcm,
    ):
        mock_nombres.return_value = {10: "Suc Centro", 20: "Suc Norte"}
        mock_fetch.return_value = {
            9001: {
                "CodigoMovimiento": 9001,
                "NroComprobante": "0001-9001",
                "Anulado": "No",
                "Estado": "pendiente",
                "autorizacion": "No Autorizado",
                "estado_aprobacion_comercial": "pendiente",
                "ImporteVenta": 1000,
                "total_calc": 1000,
                "id_cliente_domicilio": 10,
            },
            9002: {
                "CodigoMovimiento": 9002,
                "NroComprobante": "0001-9002",
                "Anulado": "Si",
                "Estado": "pendiente",
                "autorizacion": "",
                "estado_aprobacion_comercial": "pendiente",
                "ImporteVenta": 500,
                "total_calc": 500,
                "id_cliente_domicilio": 20,
            },
        }
        payload = construir_resumen_lote(self.base, self.draft.pk, self.sess)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["sucursales"]), 2)
        self.assertEqual(payload["lote"]["totales"]["ped_vivos"], 1)
        estados = {s["id_cliente_domicilio"]: s["estado_operativo"] for s in payload["sucursales"]}
        self.assertEqual(estados[10], "por_autorizar")
        self.assertEqual(estados[20], "anulada")

    @patch("ecom.services.lote_resumen._draft_en_alcance_hub", return_value=False)
    def test_fuera_alcance_403(self, _mock):
        with self.assertRaises(LoteResumenError) as ctx:
            construir_resumen_lote(self.base, self.draft.pk, self.sess)
        self.assertEqual(ctx.exception.status, 403)

    def test_draft_no_confirmado_404(self):
        self.draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        self.draft.save(update_fields=["estado"])
        with self.assertRaises(LoteResumenError) as ctx:
            construir_resumen_lote(self.base, self.draft.pk, self.sess)
        self.assertEqual(ctx.exception.status, 404)

    @patch("ecom.services.lote_resumen.listar_sucursales_cliente", return_value=_sucursales_vcm_mock())
    @patch("ecom.services.lote_resumen.puede_aprobar_lote", return_value=False)
    @patch("ecom.services.lote_resumen.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.lote_resumen._nombre_cliente", return_value="ACME SA")
    @patch("ecom.services.lote_resumen._mapa_nombres_sucursales")
    @patch("ecom.services.lote_resumen._fetch_pedidos_lote_detalle")
    @patch("ecom.services.lote_resumen._draft_en_alcance_hub", return_value=True)
    def test_sucursal_no_generada_sin_ped_mysql(
        self,
        _mock_alcance,
        mock_fetch,
        mock_nombres,
        _mock_nombre_cli,
        _mock_aprob,
        _mock_puede,
        _mock_vcm,
    ):
        """REQ-LOT-04: PED en codigos_movimiento[] ausente en MySQL → No generada."""
        mock_nombres.return_value = {10: "Suc Centro", 20: "Suc Norte"}
        mock_fetch.return_value = {
            9001: {
                "CodigoMovimiento": 9001,
                "NroComprobante": "0001-9001",
                "Anulado": "No",
                "Estado": "pendiente",
                "autorizacion": "No Autorizado",
                "estado_aprobacion_comercial": "pendiente",
                "ImporteVenta": 1000,
                "total_calc": 1000,
                "id_cliente_domicilio": 10,
            },
        }
        payload = construir_resumen_lote(self.base, self.draft.pk, self.sess)
        estados = {s["id_cliente_domicilio"]: s["estado_operativo"] for s in payload["sucursales"]}
        etiquetas = {s["id_cliente_domicilio"]: s["estado_operativo_label"] for s in payload["sucursales"]}
        self.assertEqual(estados[10], "por_autorizar")
        self.assertEqual(estados[20], "no_generada")
        self.assertEqual(etiquetas[20], "No generada")
        self.assertEqual(payload["lote"]["totales"]["ped_vivos"], 1)

    @patch("ecom.services.lote_resumen.listar_sucursales_cliente", return_value=_sucursales_vcm_mock((10, 20)))
    @patch("ecom.services.lote_resumen.puede_aprobar_lote", return_value=False)
    @patch("ecom.services.lote_resumen.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.lote_resumen._nombre_cliente", return_value="ACME SA")
    @patch("ecom.services.lote_resumen._mapa_nombres_sucursales")
    @patch("ecom.services.lote_resumen._fetch_pedidos_lote_detalle", return_value={})
    @patch("ecom.services.lote_resumen._draft_en_alcance_hub", return_value=True)
    def test_filtra_sucursales_fuera_vcm(
        self,
        _mock_alcance,
        _mock_fetch,
        mock_nombres,
        _mock_nombre_cli,
        _mock_aprob,
        _mock_puede,
        _mock_vcm,
    ):
        """Solo sucursales VCM del viajante; celdas fuera de VCM sin PED no aparecen."""
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=self.draft,
            id_articulo=2,
            id_cliente_domicilio=30,
            cantidad_packs=Decimal("3"),
        )
        mock_nombres.return_value = {10: "Suc Centro", 20: "Suc Norte", 30: "Suc Sur"}
        payload = construir_resumen_lote(self.base, self.draft.pk, self.sess)
        ids = {s["id_cliente_domicilio"] for s in payload["sucursales"]}
        self.assertEqual(ids, {10, 20})
        self.assertNotIn(30, ids)
