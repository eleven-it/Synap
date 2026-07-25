# Tests motor aprobación comercial (REQ-APR-02, REQ-APR-03, REQ-APR-04).

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ecom.services.aprobacion_pedidos import (
    ESTADO_NEUTRO,
    ESTADO_PENDIENTE,
    aplicar_estado_inicial_checkout,
    evaluar_reglas,
    resolver,
)


class _FakeCart:
    def __init__(self, total="1000", desc_pie="0", items=None):
        self.total = Decimal(total)
        self.descuento_pie_pct = Decimal(desc_pie)
        self.idcliente = 10
        self.items = items or []


class _FakeItem:
    def __init__(self, pct):
        self.porcentaje_descuento = Decimal(pct)


class TestEvaluarReglas(unittest.TestCase):
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=False)
    def test_flags_off_sin_reglas(self, _flag):
        cart = _FakeCart(total="99999")
        req, reglas = evaluar_reglas("emp1", cart, {}, autorizacion_sistema="No Autorizado")
        self.assertFalse(req)
        self.assertEqual(reglas, [])

    @patch("ecom.services.aprobacion_pedidos.umbrales_aprobacion_pedidos")
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    def test_monto_dispara(self, _flag, mock_umbral):
        mock_umbral.return_value = {
            "monto": Decimal("500"),
            "desc_pie": None,
            "desc_renglon": None,
        }
        cart = _FakeCart(total="1000")
        req, reglas = evaluar_reglas("emp1", cart, {}, autorizacion_sistema="Autorizado")
        self.assertTrue(req)
        self.assertIn("monto", reglas)

    @patch("ecom.services.aprobacion_pedidos.credito_pedidos_activo", return_value=False)
    @patch("ecom.services.aprobacion_pedidos.umbrales_aprobacion_pedidos")
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    def test_credito_no_autorizado(self, _flag, mock_umbral, _credito_off):
        mock_umbral.return_value = {"monto": None, "desc_pie": None, "desc_renglon": None}
        cart = _FakeCart(total="100")
        req, reglas = evaluar_reglas(
            "emp1", cart, {}, autorizacion_sistema="No Autorizado"
        )
        self.assertTrue(req)
        self.assertIn("credito_no_autorizado", reglas)

    @patch("ecom.services.aprobacion_pedidos.umbrales_aprobacion_pedidos")
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    def test_desc_pie_y_renglon(self, _flag, mock_umbral):
        mock_umbral.return_value = {
            "monto": None,
            "desc_pie": Decimal("5"),
            "desc_renglon": Decimal("8"),
        }
        cart = _FakeCart(desc_pie="10", items=[_FakeItem("12")])
        req, reglas = evaluar_reglas(
            "emp1", cart, {"descRenglon": "3"}, autorizacion_sistema="Autorizado"
        )
        self.assertTrue(req)
        self.assertIn("desc_pie", reglas)
        self.assertIn("desc_renglon", reglas)


class TestAplicarEstadoCheckout(unittest.TestCase):
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    def test_pendiente_con_evento(self, _flag):
        cursor = MagicMock()
        estado = aplicar_estado_inicial_checkout(
            cursor,
            "emp1",
            cod_mov=9001,
            cod_viajante=42,
            requiere=True,
            reglas=["monto"],
        )
        self.assertEqual(estado, ESTADO_PENDIENTE)
        self.assertEqual(cursor.execute.call_count, 2)

    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=False)
    def test_flag_off_neutro(self, _flag):
        cursor = MagicMock()
        estado = aplicar_estado_inicial_checkout(
            cursor,
            "emp1",
            cod_mov=9001,
            cod_viajante=42,
            requiere=True,
            reglas=["monto"],
        )
        self.assertEqual(estado, ESTADO_NEUTRO)
        cursor.execute.assert_not_called()


class TestResolverRouting(unittest.TestCase):
    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.aprobacion_pedidos._fetch_ped_aprobacion")
    @patch("ecom.services.aprobacion_pedidos.get_mysql_pool")
    def test_supervisor_escala_a_gerente(self, mock_pool_fn, mock_fetch, _flag):
        mock_fetch.return_value = {
            "CodigoMovimiento": 9001,
            "CodViajante": 20,
            "estado_aprobacion_comercial": ESTADO_PENDIENTE,
            "Anulado": "No",
        }
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        with patch(
            "ecom.services.aprobacion_pedidos._routing_aprobadores",
            return_value=(10, 100),
        ):
            with patch(
                "ecom.services.aprobacion_pedidos._ultimo_evento_escalado",
                return_value=False,
            ):
                sess = {"synap_permisos": ["ecom.pedidos.aprobar"], "CodViajante": 10}
                with patch(
                    "ecom.services.aprobacion_pedidos.pedido_en_alcance_aprobador",
                    return_value=True,
                ):
                    ok, msg, payload = resolver(
                        "emp1", 9001, "aprobar", 10, "OK", sess_user=sess
                    )
        self.assertTrue(ok)
        self.assertTrue(payload.get("escalado"))
        self.assertEqual(payload.get("estado_aprobacion_comercial"), ESTADO_PENDIENTE)

    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=False)
    def test_flag_off_rechaza_resolver(self, _flag):
        ok, msg, _ = resolver("emp1", 9001, "aprobar", 10, "OK")
        self.assertFalse(ok)
        self.assertIn("no está activa", msg.lower())
