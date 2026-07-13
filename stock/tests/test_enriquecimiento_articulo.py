from unittest.mock import MagicMock

from django.test import SimpleTestCase

from core.services.administranet_stock import _enriquecer_renglones_desde_articulo


class TestEnriquecimientoRenglonesDesdeArticulo(SimpleTestCase):
    def test_reemplaza_codigo_y_descripcion_por_el_maestro(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (
                887,
                "1.1.883",
                "6807 T5 Puma Invisible Sneaker Aero Logo Marino 1Par",
                "1924.047004",
                "1.0000",
                "Gravado",
                "2.00",
                1,
            ),
        ]
        renglones = [
            {
                "IDArt": "887",
                "CodigoArticulo": "nombre incorrecto",
                "Descripcion": "nombre anterior",
            },
            {
                "IDArt": "999",
                "CodigoArticulo": "sin maestro",
                "Descripcion": "sin maestro",
            },
        ]

        _enriquecer_renglones_desde_articulo(cursor, renglones)

        self.assertEqual(renglones[0]["CodigoArticulo"], "1.1.883")
        self.assertEqual(
            renglones[0]["Descripcion"],
            "6807 T5 Puma Invisible Sneaker Aero Logo Marino 1Par",
        )
        self.assertEqual(renglones[0]["id_manual"], "1924.047004")
        self.assertEqual(renglones[0]["PrecioCostoxU"], 1)
        self.assertEqual(renglones[0]["TipoIVA"], "Gravado")
        self.assertEqual(renglones[0]["Alicuota"], 2)
        self.assertEqual(renglones[0]["CodLaboratorio"], 1)
        self.assertEqual(renglones[1]["CodigoArticulo"], "sin maestro")
        self.assertEqual(renglones[1]["Descripcion"], "sin maestro")
        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args.args
        self.assertIn("CodigoArticuloT", sql)
        self.assertIn("PrecioCosto", sql)
        self.assertIn("TipoIVA", sql)
        self.assertIn("Alicuota", sql)
        self.assertIn("CodLaboratorio", sql)
        self.assertEqual(params, [887, 999])

    def test_conserva_metadatos_de_renglon_y_usa_precio_costo_existente(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (887, "1.1.883", "Nombre maestro", "manual-maestro", "1.0000", "Gravado", "2.00", 1),
        ]
        renglones = [
            {
                "IDArt": 887,
                "CodigoArticulo": "codigo cliente",
                "Descripcion": "descripcion cliente",
                "id_manual": "manual-renglon",
                "PrecioCosto": "3.50",
                "PrecioCostoxU": "0",
                "TipoIVA": "Exento",
                "Alicuota": "0",
                "CodLaboratorio": 8,
            },
        ]

        _enriquecer_renglones_desde_articulo(cursor, renglones)

        self.assertEqual(renglones[0]["CodigoArticulo"], "1.1.883")
        self.assertEqual(renglones[0]["Descripcion"], "Nombre maestro")
        self.assertEqual(renglones[0]["id_manual"], "manual-renglon")
        self.assertEqual(renglones[0]["PrecioCostoxU"], "0")
        self.assertEqual(renglones[0]["TipoIVA"], "Exento")
        self.assertEqual(renglones[0]["Alicuota"], "0")
        self.assertEqual(renglones[0]["CodLaboratorio"], 8)

    def test_no_consulta_sin_idart(self):
        cursor = MagicMock()
        renglones = [{"CodigoArticulo": "sin-id", "Descripcion": "Sin ID"}]

        _enriquecer_renglones_desde_articulo(cursor, renglones)

        cursor.execute.assert_not_called()
