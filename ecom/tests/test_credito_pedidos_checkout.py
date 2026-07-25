# -*- coding: utf-8 -*-
"""Tests checkout con evaluador unificado flag ON/OFF (Fase A — TDD)."""
from decimal import Decimal
from unittest.mock import patch

from ecom.services import mayorista_checkout_service as checkout_svc
from ecom.services.mayorista_checkout_service import CheckoutInput
from ecom.tests.test_mayorista_checkout_service import CheckoutTestBase, FakeConn, FakeCursor


class CreditoCheckoutFakeCursor(FakeCursor):
    def execute(self, sql, params=None):
        low = " ".join(sql.split()).lower()
        if "from ecom_credito_politica" in low:
            self._last = None
        elif "insert into ecom_credito_evaluacion" in low:
            self.state["credito_eval_inserts"] = self.state.get("credito_eval_inserts", 0) + 1
            self.state["credito_eval_params"] = params
        elif "insert into ecom_credito_evento" in low:
            self.state["credito_evento_count"] = self.state.get("credito_evento_count", 0) + 1
        elif "update comp_ped" in low and "estado_credito_finanzas" in low:
            self.state["credito_finanzas_update"] = params
        elif "from cliente" in low and "saldo" in low:
            self._last = {"monto": self.state.get("cliente_saldo", Decimal("0"))}
        elif "tipocomprobante = 'ped'" in low and "sum" in low:
            self._last = {"monto": self.state.get("ped_abiertos", Decimal("0"))}
        else:
            super().execute(sql, params)


class CreditoCheckoutTests(CheckoutTestBase):
    @patch.object(checkout_svc, "aprobacion_pedidos_activa", return_value=False)
    @patch.object(checkout_svc, "credito_pedidos_activo", return_value=False)
    def test_flag_off_usa_legacy_solo_dias(self, _flag, _apr):
        state = {"codmov": 1000, "talonario": {"Nro": 57, "PV": 3}, "ultimaf": None}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(
                cart,
                CheckoutInput(tipo="PED", id_punto_venta=3, enviar_mail_cliente=False),
                id_usuario=5,
            )
        self.assertTrue(ok, err)
        self.assertEqual(result["autorizacion"], "Autorizado")
        self.assertEqual(state.get("credito_eval_inserts", 0), 0)
        sqls = " ".join(s for s, _ in conn.cur.executed).lower()
        self.assertIn("cuentacliente", sqls)
        self.assertNotIn("ecom_credito_evaluacion", sqls)

    @patch("ecom.services.credito_pedidos.avisos.disparar_aviso_pedido_bloqueado")
    @patch("ecom.services.credito_pedidos.aprobacion.credito_hold_prep_activo", return_value=False)
    @patch("ecom.services.credito_pedidos.aprobacion.credito_pedidos_activo", return_value=True)
    @patch.object(checkout_svc, "aprobacion_pedidos_activa", return_value=False)
    @patch.object(checkout_svc, "credito_pedidos_activo", return_value=True)
    def test_flag_on_persiste_snapshot_y_alta_no_bloqueada(
        self, _flag, _apr, _apr_mod, _hold, _aviso
    ):
        state = {
            "codmov": 1000,
            "talonario": {"Nro": 57, "PV": 3},
            "ultimaf": None,
            "cliente_saldo": Decimal("5000"),
            "ped_abiertos": Decimal("0"),
        }
        conn = FakeConn(state)
        conn.cursor = lambda *a, **k: CreditoCheckoutFakeCursor(state)
        cart = self._cart(tipo="PED")
        cli = self._cli()
        cli["Credito"] = Decimal("1000")
        with self._with_patches(conn, cli=cli):
            ok, err, result = checkout_svc.confirmar(
                cart,
                CheckoutInput(tipo="PED", id_punto_venta=3, enviar_mail_cliente=False),
                id_usuario=5,
            )
        self.assertTrue(ok, err)
        self.assertEqual(result["autorizacion"], "No Autorizado")
        self.assertEqual(state.get("credito_eval_inserts"), 1)
        self.assertEqual(state.get("comp_ped_count"), 1)
