"""Tests backlog gestión pedidos: PRE→PED, anulación, presentación, mail."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from ecom.services.comprobantes_anulacion import anular_pedido_relay
from ecom.services.presentacion_articulo import (
    _fetch_articulo_prov,
    cantidad_base_desde_ui,
    multiplicador_presentacion,
    opciones_presentacion_articulo,
)
from ecom.services.presupuesto_a_pedido_service import validar_presupuesto_convertible


class TestPresentacionArticulo(TestCase):
    def test_multiplicador_pallet(self):
        prov = {
            "cantidad_unidad_display": 6,
            "cantidad_display_bulto": 4,
            "cantidad_bulto_pallet": 10,
        }
        m = multiplicador_presentacion("Pallet", prov)
        self.assertEqual(m, Decimal("240"))

    def test_cantidad_base_desde_ui(self):
        q = cantidad_base_desde_ui(2, "Display", multiplicador=6)
        self.assertEqual(q, Decimal("12"))

    @patch("ecom.services.presentacion_articulo.get_mysql_pool")
    def test_fetch_articulo_prov_no_usa_multiplicador_vta(self, mock_pool):
        """articulo_prov legacy no tiene multiplicador_vta; la consulta no debe referenciarla."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.description = [
            ("cantidad_uni",),
            ("cantidad_unidad_display",),
            ("cantidad_display_bulto",),
            ("cantidad_bulto_pallet",),
        ]
        mock_cur.fetchone.return_value = (1, 6, 4, 10)
        mock_pool.return_value.get_connection.return_value.__enter__ = lambda s: mock_conn
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        out = _fetch_articulo_prov("emp1", 127)
        sql = mock_cur.execute.call_args[0][0]
        self.assertNotIn("multiplicador_vta", sql.lower())
        self.assertIn("codproveedor", sql.lower())
        self.assertEqual(out["cantidad_unidad_display"], 6)

    @patch("ecom.services.presentacion_articulo.get_mysql_pool")
    def test_fetch_articulo_prov_tolera_error_sql(self, mock_pool):
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("1054 unknown column")
        mock_pool.return_value.get_connection.return_value.__enter__ = lambda s: mock_conn
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        self.assertEqual(_fetch_articulo_prov("emp1", 127), {})


class TestAnulacionMotivo(TestCase):
    @patch("ecom.services.comprobantes_anulacion.puede_anular_pedido_relay")
    def test_motivo_obligatorio(self, mock_puede):
        mock_puede.return_value = (True, "")
        r = anular_pedido_relay("b", 1, motivo="")
        self.assertEqual(r["msg"], "error")
        self.assertIn("motivo", r["error"].lower())


class TestPresupuestoConvertir(TestCase):
    @patch("ecom.services.presupuesto_a_pedido_service.detalle_pedido_relay")
    @patch("ecom.services.presupuesto_a_pedido_service.cabecera_comprobante_relay")
    @patch("ecom.services.presupuesto_a_pedido_service._ya_convertido")
    def test_validar_pre_ok(self, mock_ya, mock_cab, mock_det):
        mock_ya.return_value = False
        mock_cab.return_value = {
            "anulado": "No",
            "estado": "Pendiente",
            "id_cliente": 10,
        }
        mock_det.return_value = [{"IDArt": 1, "Salida": 2}]
        cab, err = validar_presupuesto_convertible("b", 99)
        self.assertIsNone(err)
        self.assertIsNotNone(cab)

    @patch("ecom.services.presupuesto_a_pedido_service.cabecera_comprobante_relay")
    def test_validar_pre_en_pedido(self, mock_cab):
        mock_cab.return_value = {"anulado": "No", "estado": "En Pedido"}
        cab, err = validar_presupuesto_convertible("b", 99)
        self.assertIsNone(cab)
        self.assertIn("convertido", err.lower())
