"""Tests básicos — autorización de lote masivo (Phase 5)."""

from unittest.mock import patch

from django.test import TestCase

from ecom.models import EcomPedidoMasivoDraft
from ecom.services.aprobacion_pedidos import (
    pedido_en_lote_pendiente,
    resolver,
    resolver_lote_masivo,
)


class TestAprobacionLote(TestCase):
    def setUp(self):
        self.base = "test_base"
        self.sess = {
            "id_usuario": 1,
            "base_empresa": self.base,
            "synap_permisos": ["ecom.pedidos.aprobar"],
        }
        self.draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa=self.base,
            id_usuario=1,
            id_cliente=50,
            cod_viajante=10,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMADO,
            codigos_movimiento=[101, 102],
            estado_aprobacion_lote=EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_PENDIENTE,
        )

    def test_pedido_en_lote_pendiente_true(self):
        self.assertTrue(pedido_en_lote_pendiente(self.base, 101))

    def test_pedido_suelto_no_bloqueado(self):
        self.assertFalse(pedido_en_lote_pendiente(self.base, 9999))

    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.aprobacion_pedidos.pedido_en_lote_pendiente", return_value=True)
    def test_resolver_individual_bloqueado_por_lote(self, _mock_lote, _mock_flag):
        ok, msg, _ = resolver(self.base, 101, "aprobar", 10, "ok", sess_user=self.sess)
        self.assertFalse(ok)
        self.assertIn("lote masivo pendiente", msg.lower())

    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=False)
    def test_resolver_lote_subflag_off(self, _mock):
        ok, msg, _ = resolver_lote_masivo(
            self.base, self.draft, "aprobar", 10, "ok", sess_user=self.sess
        )
        self.assertFalse(ok)
        self.assertIn("no está activa", msg.lower())

    @patch("ecom.services.aprobacion_pedidos._sincronizar_estado_lote_tras_resolver", return_value="aprobado")
    @patch("ecom.services.aprobacion_pedidos.resolver")
    @patch("ecom.services.aprobacion_pedidos._codigos_ped_activos_lote", return_value=[101, 102])
    @patch("ecom.services.aprobacion_pedidos._snapshot_estado_comercial", return_value="pendiente")
    @patch("ecom.services.aprobacion_pedidos.puede_aprobar_lote", return_value=True)
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    def test_resolver_lote_ok(
        self,
        _flag,
        _puede,
        _snap,
        _activos,
        mock_resolver,
        _sync,
    ):
        mock_resolver.side_effect = [
            (True, "ok1", {"estado_aprobacion_comercial": "aprobado"}),
            (True, "ok2", {"estado_aprobacion_comercial": "aprobado"}),
        ]
        ok, msg, payload = resolver_lote_masivo(
            self.base, self.draft, "aprobar", 10, "ok", sess_user=self.sess
        )
        self.assertTrue(ok)
        self.assertEqual(payload.get("resueltos"), 2)
        self.assertEqual(mock_resolver.call_count, 2)

    @patch("ecom.services.aprobacion_pedidos._revertir_estados_comerciales", return_value=[])
    @patch("ecom.services.aprobacion_pedidos.resolver")
    @patch("ecom.services.aprobacion_pedidos._codigos_ped_activos_lote", return_value=[101, 102])
    @patch("ecom.services.aprobacion_pedidos._snapshot_estado_comercial", return_value="pendiente")
    @patch("ecom.services.aprobacion_pedidos.puede_aprobar_lote", return_value=True)
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    def test_resolver_lote_compensa_fallo_parcial(
        self,
        _flag,
        _puede,
        _snap,
        _activos,
        mock_resolver,
        mock_revert,
    ):
        mock_resolver.side_effect = [
            (True, "ok1", {"estado_aprobacion_comercial": "aprobado"}),
            (False, "fallo PED 102", None),
        ]
        ok, msg, payload = resolver_lote_masivo(
            self.base, self.draft, "aprobar", 10, "ok", sess_user=self.sess
        )
        self.assertFalse(ok)
        mock_revert.assert_called_once()
        self.assertEqual(payload.get("estado_aprobacion_lote"), "error")
        self.draft.refresh_from_db()
        self.assertEqual(
            self.draft.estado_aprobacion_lote,
            EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_ERROR,
        )

    @patch("ecom.services.aprobacion_pedidos._sincronizar_estado_lote_tras_resolver", return_value="pendiente")
    @patch("ecom.services.aprobacion_pedidos.resolver")
    @patch("ecom.services.aprobacion_pedidos._codigos_ped_activos_lote", return_value=[101, 102])
    @patch("ecom.services.aprobacion_pedidos._snapshot_estado_comercial", return_value="pendiente")
    @patch("ecom.services.aprobacion_pedidos.puede_aprobar_lote", return_value=True)
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    def test_resolver_lote_escalado_no_es_fallo(
        self,
        _flag,
        _puede,
        _snap,
        _activos,
        mock_resolver,
        _sync,
    ):
        """REQ-APR-05: escalado Supervisor→Gerente es resultado válido, no compensación."""
        mock_resolver.side_effect = [
            (True, "escalado", {"estado_aprobacion_comercial": "pendiente", "escalado": True}),
            (True, "ok", {"estado_aprobacion_comercial": "aprobado"}),
        ]
        ok, msg, payload = resolver_lote_masivo(
            self.base, self.draft, "aprobar", 10, "ok", sess_user=self.sess
        )
        self.assertTrue(ok)
        self.assertEqual(payload.get("escalados"), 1)
        self.assertEqual(payload.get("resueltos"), 1)
        self.assertIn("escalado", msg.lower())
        self.assertEqual(payload.get("estado_aprobacion_lote"), "pendiente")
