from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from ecom.mayoristapp_listado_views import SaldosClientesMayoristappView
from ecom.services.cartera_saldos import listar_saldos_clientes


class TestCarteraSaldos(SimpleTestCase):
    @patch("ecom.services.cartera_saldos.mysql_cursor")
    @patch("ecom.services.cartera_saldos.where_vendedor_cliente", return_value=(" AND cliente.CodViajante IN (%s,%s) ", [7, 8]))
    def test_vendedor_solo_su_cartera(self, _alcance, mysql_cursor):
        cursor = mysql_cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [{
            "Codigo": 904, "nombre_cliente": "Tutuca", "cuit": "30-123",
            "saldo": "2354.25", "vendedor": "Ricardo",
        }]
        filas = listar_saldos_clientes("bestsox", {"id_usuario": 1})
        self.assertEqual(filas[0]["saldo"], Decimal("2354.25"))
        sql, params = cursor.execute.call_args.args
        self.assertIn("cliente.CodViajante IN (%s,%s)", sql)
        self.assertEqual(params, [7, 8])

    @patch("ecom.services.cartera_saldos.mysql_cursor")
    @patch("ecom.services.cartera_saldos.where_vendedor_cliente", return_value=(" AND 1=0 ", []))
    def test_sin_cartera_no_consulta_todos(self, _alcance, mysql_cursor):
        cursor = mysql_cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        self.assertEqual(listar_saldos_clientes("bestsox", {}), [])
        self.assertIn("AND 1=0", cursor.execute.call_args.args[0])

    def test_csv_contiene_saldo_y_cabecera(self):
        request = RequestFactory().get("/ecom/mayoristapp/cartera/saldos/?formato=csv")
        view = SaldosClientesMayoristappView()
        view.request = request
        with patch.object(view, "_filas", return_value=[{
            "codigo": 904, "nombre": "Tutuca", "cuit": "30-123",
            "vendedor": "Ricardo", "saldo": Decimal("2354.25"),
        }]):
            response = view.get(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("2354,25", response.content.decode("utf-8"))
