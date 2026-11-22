from unittest.mock import patch

from django.test import SimpleTestCase

from ecom.services.pedido_cabecera_relay import entrega_renglones_pedido, vinculos_pedido_relay


class TestVinculosFacturas(SimpleTestCase):
    @patch("ecom.services.pedido_cabecera_relay._fetch_all")
    def test_factura_asociada_al_remito_del_pedido(self, fetch):
        fetch.side_effect = [
            [
                {"codigo_movimiento_remito": 20, "nro_comprobante": "REM 20"},
                {"codigo_movimiento_remito": 21, "nro_comprobante": "REM 21"},
            ],
            [{"codigo_movimiento_remito": 21, "codigo_movimiento_factura": 42,
              "nro_comprobante": "FA 42", "fecha": "14/11/2026"}],
        ]
        vinculos = vinculos_pedido_relay("bestsox", 9)
        self.assertEqual(vinculos[0]["facturas"], [])
        self.assertEqual(vinculos[1]["facturas"][0]["nro_comprobante"], "FA 42")
        self.assertEqual(fetch.call_args.args[2], [20, 21])

    @patch("ecom.services.pedido_cabecera_relay._fetch_all")
    def test_entrega_parcial_reparte_articulo_repetido(self, fetch):
        fetch.return_value = [{"id_articulo": 10, "entregado": "7"}]
        filas, resumen = entrega_renglones_pedido("bestsox", 9, [
            {"IDArt": 10, "Salida": "5"},
            {"IDArt": 10, "Salida": "5"},
        ])
        self.assertEqual([f["cantidad_pendiente"] for f in filas], [0, 3])
        self.assertEqual(resumen["estado"], "parcial")
        self.assertEqual(resumen["pendiente"], 3)

    @patch("ecom.services.pedido_cabecera_relay._fetch_all", return_value=[])
    def test_sin_remito_todo_esta_pendiente(self, _fetch):
        filas, resumen = entrega_renglones_pedido("bestsox", 9, [{"IDArt": 10, "Salida": "5"}])
        self.assertEqual(filas[0]["cantidad_pendiente"], 5)
        self.assertEqual(resumen["estado"], "sin_entrega")
