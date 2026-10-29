"""Alcance de cartera del nuevo acceso a cobranzas."""

from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from ecom.services.cliente_relay import _sesion_para_cartera
from ecom.services.comprobantes_no_cancelados_relay import _where, listar_no_cancelados_relay


class TestSesionParaCartera(SimpleTestCase):
    def test_vendedor_ignora_acceso_ampliado_y_usa_viajante_propio(self):
        sesion = {
            "nombre_puesto": "Vendedores ecom",
            "id_vendedor_usr": 12,
            "todos_clientes": "Si",
            "supervisor_venta": "Si",
            "vendedor_a_cargo": [13],
            "cod_viajante_operativo": 13,
        }
        filtrada = _sesion_para_cartera(sesion, True)
        self.assertEqual(filtrada["id_vendedor_usr"], 12)
        self.assertEqual(filtrada["todos_clientes"], "No")
        self.assertEqual(filtrada["supervisor_venta"], "No")
        self.assertEqual(filtrada["vendedor_a_cargo"], [])
        self.assertIsNone(filtrada["cod_viajante_operativo"])
        self.assertEqual(sesion["todos_clientes"], "Si")

    def test_preventista_aplica_mismo_alcance(self):
        self.assertEqual(
            _sesion_para_cartera({"nombre_puesto": "Preventista", "todos_clientes": "Si"}, True)["todos_clientes"],
            "No",
        )

    def test_supervisor_y_administracion_conservan_acceso_ampliado(self):
        for puesto in ("Supervisor", "Supervisor venta", "Administración"):
            with self.subTest(puesto=puesto):
                sesion = {"nombre_puesto": puesto, "todos_clientes": "Si"}
                self.assertIs(_sesion_para_cartera(sesion, True), sesion)


class TestComprobantesACobrar(SimpleTestCase):
    def test_solo_facturas_y_notas_credito_con_saldo(self):
        condiciones, params = _where({"solo_cobranzas": True}, 1010, False)
        sql = " AND ".join(condiciones)
        self.assertIn("'FA'", sql)
        self.assertIn("'NCA'", sql)
        self.assertNotIn("'NDA'", sql)
        self.assertNotIn("'REC'", sql)
        self.assertIn("recibo_factura.Saldo > 0", sql)
        self.assertEqual(params, [1010])

    @patch("ecom.services.comprobantes_no_cancelados_relay.get_mysql_pool")
    def test_nota_credito_sin_imputar_resta_del_total(self, mock_pool):
        cursor = MagicMock()
        cursor.description = [("TipoComprobante",), ("Saldo",)]
        cursor.fetchall.return_value = [("FA", 100), ("NCA", 20)]
        mock_pool.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value = cursor
        resultado = listar_no_cancelados_relay("administranet2", {"solo_cobranzas": True}, 1010)
        self.assertIn("DATEDIFF(CURDATE(), recibo_factura.Vencimiento)", cursor.execute.call_args.args[0])
        self.assertEqual(resultado["saldo_al_dia"], 80)
        self.assertEqual([fila["SaldoSigned"] for fila in resultado["filas"]], [100, -20])
        self.assertEqual([fila["SaldoAcum"] for fila in resultado["filas"]], [100, 80])
