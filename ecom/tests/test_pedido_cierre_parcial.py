"""El cierre parcial conserva lo entregado y libera solo el pendiente."""

from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.pedido_gestion_views import PedidoCierreParcialAPIView
from ecom.services.pedido_cierre_parcial import cerrar_pedido_parcial


class _Cursor:
    def __init__(self, reserva=Decimal("6"), entregado=Decimal("4")):
        self.reserva = reserva
        self.entregado = entregado
        self.sql = ""
        self.calls = []

    def execute(self, sql, params):
        self.sql = sql
        self.calls.append((sql, params))

    def fetchone(self):
        if "FROM comp_ped" in self.sql:
            return ("En preparación", "No")
        if "FROM stock_deposito" in self.sql:
            return (self.reserva,)
        return None

    def fetchall(self):
        if "FROM stockp" in self.sql:
            return [(123, Decimal("10"), 2)]
        if "FROM stock s" in self.sql:
            return [(123, self.entregado)] if self.entregado else []
        return []


class _Connection:
    def __init__(self, cur):
        self.cur = cur
        self.committed = False
        self.rolled_back = False

    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def cursor(self): return self.cur
    def autocommit(self, _value): pass
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True


class PedidoCierreParcialTests(SimpleTestCase):
    def _ejecutar(self, reserva, entregado):
        conn = _Connection(_Cursor(reserva, entregado))
        class Pool:
            def get_connection(self, _base): return conn
        with patch("ecom.services.pedido_cierre_parcial.get_mysql_pool", return_value=Pool()):
            result = cerrar_pedido_parcial("bestsox", 99, "Cliente no espera saldo")
        return result, conn

    def test_libera_solo_seis_unidades_pendientes(self):
        result, conn = self._ejecutar(Decimal("6"), Decimal("4"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["liberado"], "6")
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)
        sql, params = next((s, p) for s, p in conn.cur.calls if s.startswith("UPDATE stock_deposito"))
        self.assertIn("saldo_pedido_cliente-%s", sql)
        self.assertEqual(params, [Decimal("6"), 123, 2])
        self.assertTrue(any("Estado='Cerrado'" in s for s, _ in conn.cur.calls))
        self.assertTrue(any("cantidad_pendiente=0" in s for s, _ in conn.cur.calls))

    def test_sin_entrega_no_cierra(self):
        result, conn = self._ejecutar(Decimal("10"), Decimal("0"))
        self.assertFalse(result["ok"])
        self.assertTrue(conn.rolled_back)

    def test_reserva_insuficiente_revierte(self):
        result, conn = self._ejecutar(Decimal("5"), Decimal("4"))
        self.assertFalse(result["ok"])
        self.assertTrue(conn.rolled_back)
        self.assertFalse(conn.committed)

    def test_api_rechaza_pedido_fuera_del_listado_visible(self):
        class Vendedor:
            is_authenticated = True
            is_superuser = False
            def tiene_permiso(self, codigo): return codigo == "ecom.pedidos.aprobar"

        req = APIRequestFactory().post(
            "/ecom/api/mayoristapp/comprobantes/pedidos/99/cierre-parcial/",
            {"motivo": "Cliente no espera saldo"}, format="json",
        )
        SessionMiddleware(lambda _: HttpResponse()).process_request(req)
        req.session["user"] = {"base_empresa": "bestsox", "tipousuario": "Vendedor"}
        force_authenticate(req, user=Vendedor())
        with patch("ecom.pedido_gestion_views.construir_hub_pedidos", return_value={"items": []}), patch(
            "ecom.pedido_gestion_views.cerrar_pedido_parcial"
        ) as cierre:
            resp = PedidoCierreParcialAPIView.as_view()(req, cod_mov=99)
        self.assertEqual(resp.status_code, 404)
        cierre.assert_not_called()
