"""Tests Fase 1 — armado surtido multi-pack (lote / carrito)."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from mpr.services import (
    LOTE_ARMADO_SURTIDO_MAX_ITEMS,
    calcular_demanda_agregada_lote,
    calcular_demanda_item_lote,
    ejecutar_lote_armado_surtido,
    normalizar_armados_lote_json,
    normalizar_item_lote_armado_surtido,
    parse_cabecera_lote_armado_surtido,
    parse_lote_armado_surtido_post,
    validar_reglas_item_candidato_lote,
    validar_reglas_lote_armado_surtido,
    validar_stock_agregado_lote,
)


def _item(pack_id: int, packs: int, componentes: list) -> dict:
    return {
        "id_articulo_pack": pack_id,
        "cantidad_packs": packs,
        "lineas": componentes,
    }


class CalcularDemandaLoteTest(SimpleTestCase):
    def test_demanda_item_simple(self):
        demanda = calcular_demanda_item_lote(
            _item(100, 2, [{"id_articulo": 813, "cantidad_por_pack": 3}])
        )
        self.assertEqual(demanda[813], Decimal("6"))

    def test_demanda_agregada_dos_packs_mismo_componente(self):
        armados = [
            _item(100, 2, [{"id_articulo": 813, "cantidad_por_pack": 3}]),
            _item(200, 1, [{"id_articulo": 813, "cantidad_por_pack": 2}]),
        ]
        demanda = calcular_demanda_agregada_lote(armados)
        self.assertEqual(demanda[813], Decimal("8"))


class NormalizarLoteJsonTest(SimpleTestCase):
    def test_parse_lista_armados(self):
        data = {
            "armados": [
                {
                    "id_articulo_pack": 1342,
                    "cantidad_packs": 1,
                    "lineas": [{"id_articulo": 813, "cantidad_por_pack": 3}],
                }
            ]
        }
        armados, err = normalizar_armados_lote_json(data)
        self.assertIsNone(err)
        self.assertEqual(len(armados), 1)
        self.assertEqual(armados[0]["id_articulo_pack"], 1342)

    def test_rechaza_json_sin_armados(self):
        armados, err = normalizar_armados_lote_json({})
        self.assertIsNone(armados)
        self.assertIn("armados", (err or "").lower())


class ValidarReglasLoteTest(SimpleTestCase):
    def test_acepta_lote_valido(self):
        armados = [
            _item(100, 1, [{"id_articulo": 813, "cantidad_por_pack": 1}]),
            _item(200, 2, [{"id_articulo": 900, "cantidad_por_pack": 1}]),
        ]
        ok, err = validar_reglas_lote_armado_surtido(
            armados,
            deposito_origen=3,
            deposito_destino=5,
            id_operario=10,
        )
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_rechaza_pack_duplicado(self):
        armados = [
            _item(100, 1, [{"id_articulo": 813, "cantidad_por_pack": 1}]),
            _item(100, 2, [{"id_articulo": 900, "cantidad_por_pack": 1}]),
        ]
        ok, err = validar_reglas_lote_armado_surtido(armados)
        self.assertFalse(ok)
        self.assertIn("fila existente", (err or "").lower())

    def test_rechaza_cruce_pack_componente(self):
        armados = [
            _item(100, 1, [{"id_articulo": 813, "cantidad_por_pack": 1}]),
            _item(200, 1, [{"id_articulo": 100, "cantidad_por_pack": 1}]),
        ]
        ok, err = validar_reglas_lote_armado_surtido(armados)
        self.assertFalse(ok)
        self.assertIn("pack y componente", (err or "").lower())

    def test_rechaza_mas_de_20_items(self):
        armados = [
            _item(1000 + i, 1, [{"id_articulo": 8000 + i, "cantidad_por_pack": 1}])
            for i in range(LOTE_ARMADO_SURTIDO_MAX_ITEMS + 1)
        ]
        ok, err = validar_reglas_lote_armado_surtido(armados)
        self.assertFalse(ok)
        self.assertIn("20", err or "")

    def test_rechaza_lote_vacio_al_ejecutar(self):
        ok, err = validar_reglas_lote_armado_surtido([], require_non_empty=True)
        self.assertFalse(ok)
        self.assertIn("al menos un armado", (err or "").lower())


class ValidarItemCandidatoLoteTest(SimpleTestCase):
    def test_agrega_si_no_hay_conflicto(self):
        lote = [_item(100, 1, [{"id_articulo": 813, "cantidad_por_pack": 1}])]
        candidato = {
            "id_articulo_pack": 200,
            "cantidad_packs": 1,
            "lineas": [{"id_articulo": 900, "cantidad_por_pack": 2}],
        }
        ok, err = validar_reglas_item_candidato_lote(lote, candidato)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_rechaza_pack_ya_en_lote(self):
        lote = [_item(100, 1, [{"id_articulo": 813, "cantidad_por_pack": 1}])]
        ok, err = validar_reglas_item_candidato_lote(lote, _item(100, 2, [{"id_articulo": 813, "cantidad_por_pack": 1}]))
        self.assertFalse(ok)


class ParseLotePostTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_parse_post_valido(self):
        lote = {
            "armados": [
                {
                    "id_articulo_pack": 1342,
                    "cantidad_packs": 2,
                    "lineas": [{"id_articulo": 813, "cantidad_por_pack": 3}],
                }
            ]
        }
        request = self.factory.post(
            "/mpr/armado-surtido/",
            {
                "lote_json": json.dumps(lote),
                "deposito_origen": "3",
                "deposito_destino": "5",
                "id_operario": "12",
                "detalle": "Turno tarde",
            },
        )
        cabecera, armados, err = parse_lote_armado_surtido_post(request)
        self.assertIsNone(err)
        self.assertEqual(cabecera["deposito_origen"], 3)
        self.assertEqual(cabecera["id_operario"], 12)
        self.assertEqual(cabecera["detalle"], "Turno tarde")
        self.assertEqual(len(armados), 1)
        self.assertEqual(armados[0]["cantidad_packs"], 2)

    def test_rechaza_sin_lote_json(self):
        request = self.factory.post("/mpr/armado-surtido/", {"deposito_origen": "3"})
        cabecera, armados, err = parse_lote_armado_surtido_post(request)
        self.assertIsNotNone(err)
        self.assertIsNone(armados)
        self.assertIsNotNone(cabecera)

    def test_cabecera_desde_post(self):
        cab = parse_cabecera_lote_armado_surtido(
            {"deposito_origen": "10", "deposito_destino": "20", "id_lista": "22"}
        )
        self.assertEqual(cab["deposito_origen"], 10)
        self.assertEqual(cab["id_lista_produccion"], 22)


class NormalizarItemLoteTest(SimpleTestCase):
    def test_item_valido(self):
        item, err = normalizar_item_lote_armado_surtido(
            _item(100, 3, [{"id_articulo": 1, "cantidad_por_pack": 2}])
        )
        self.assertIsNone(err)
        self.assertEqual(item["cantidad_packs"], 3)

    def test_sin_componentes(self):
        item, err = normalizar_item_lote_armado_surtido(_item(100, 1, []))
        self.assertIsNone(item)
        self.assertIn("componente", (err or "").lower())


class ValidarStockAgregadoLoteTest(SimpleTestCase):
    @patch("mpr.services._articulos_con_lote_ids", return_value=set())
    @patch("mpr.services._fetch_articulos_map", return_value={813: {"codigo_articulo": "1.1.813"}})
    @patch("mpr.services._nombre_tabla", side_effect=lambda _c, t: t)
    @patch("mpr.services.mysql_cursor")
    def test_detecta_conflicto_stock(self, mock_mysql, *_mocks):
        cursor = MagicMock()
        cursor.fetchall.return_value = [{"id_articulo": 813, "saldo": 5}]
        mock_mysql.return_value.__enter__.return_value = cursor
        armados = [_item(100, 2, [{"id_articulo": 813, "cantidad_por_pack": 3}])]
        ok, conflictos = validar_stock_agregado_lote("emp", 3, armados)
        self.assertFalse(ok)
        self.assertEqual(len(conflictos), 1)
        self.assertEqual(conflictos[0]["id_articulo"], 813)
        self.assertEqual(conflictos[0]["necesario"], 6.0)
        self.assertEqual(conflictos[0]["disponible"], 5.0)

    @patch("mpr.services._articulos_con_lote_ids", return_value=set())
    @patch("mpr.services._fetch_articulos_map", return_value={813: {"codigo_articulo": "1.1.813"}})
    @patch("mpr.services._nombre_tabla", side_effect=lambda _c, t: t)
    @patch("mpr.services.mysql_cursor")
    def test_acepta_stock_suficiente(self, mock_mysql, *_mocks):
        cursor = MagicMock()
        cursor.fetchall.return_value = [{"id_articulo": 813, "saldo": 10}]
        mock_mysql.return_value.__enter__.return_value = cursor
        armados = [_item(100, 2, [{"id_articulo": 813, "cantidad_por_pack": 3}])]
        ok, conflictos = validar_stock_agregado_lote("emp", 3, armados)
        self.assertTrue(ok)
        self.assertEqual(conflictos, [])


class EjecutarLoteArmadoSurtidoTest(SimpleTestCase):
    def _cabecera(self):
        return {
            "deposito_origen": 3,
            "deposito_destino": 5,
            "id_operario": 10,
            "detalle": "Turno",
        }

    @patch("mpr.models.MprArmadoLote")
    @patch("mpr.services.guardar_composicion_armado_surtido")
    @patch("mpr.services.get_connection")
    @patch("mpr.services.articulo_habilitado_armado_surtido", return_value=True)
    @patch("mpr.services._ejecutar_armado_surtido_tx")
    def test_parcial_falla_segundo_item(self, mock_tx, *_mocks):
        lote_mock = MagicMock()
        lote_mock.id = "00000000-0000-0000-0000-000000000001"
        _mocks[3].objects.create.return_value = lote_mock
        mock_tx.side_effect = [
            (True, 11, "0001-00000011", None, [{"id_articulo": 813}], {
                "codigo_articulo_pack": "1.1.100",
                "descripcion_articulo_pack": "Pack A",
                "saldo_inicial": 5.0,
                "saldo_final": 6.0,
            }),
            (False, None, None, "Stock insuficiente", [], None),
            (True, 13, "0001-00000013", None, [{"id_articulo": 900}], {
                "codigo_articulo_pack": "1.1.300",
                "descripcion_articulo_pack": "Pack C",
                "saldo_inicial": 0.0,
                "saldo_final": 1.0,
            }),
        ]
        conn = MagicMock()
        _mocks[1].return_value.__enter__.return_value = conn
        armados = [
            _item(100, 1, [{"id_articulo": 813, "cantidad_por_pack": 1}]),
            _item(200, 1, [{"id_articulo": 813, "cantidad_por_pack": 5}]),
            _item(300, 1, [{"id_articulo": 900, "cantidad_por_pack": 1}]),
        ]
        resultado = ejecutar_lote_armado_surtido("emp", 1, self._cabecera(), armados)
        self.assertEqual(len(resultado["exitosos"]), 2)
        self.assertEqual(len(resultado["fallidos"]), 1)
        self.assertEqual(resultado["exitosos"][0]["codigo_movimiento"], 11)
        self.assertEqual(resultado["exitosos"][0]["descripcion_pack"], "1.1.100 — Pack A")
        self.assertEqual(resultado["exitosos"][0]["saldo_inicial"], 5.0)
        self.assertEqual(resultado["exitosos"][0]["saldo_final"], 6.0)
        self.assertEqual(resultado["exitosos"][0]["cantidad_grabada"], 1)
        self.assertEqual(resultado["exitosos"][1]["codigo_movimiento"], 13)
        self.assertIn("Stock insuficiente", resultado["fallidos"][0]["error"])
        self.assertEqual(mock_tx.call_count, 3)

    @patch("mpr.services.articulo_habilitado_armado_surtido", return_value=True)
    @patch("mpr.services._ejecutar_armado_surtido_tx")
    def test_error_global_reglas_lote(self, mock_tx, *_mocks):
        armados = [
            _item(100, 1, [{"id_articulo": 813, "cantidad_por_pack": 1}]),
            _item(100, 2, [{"id_articulo": 900, "cantidad_por_pack": 1}]),
        ]
        resultado = ejecutar_lote_armado_surtido("emp", 1, self._cabecera(), armados)
        self.assertEqual(resultado["exitosos"], [])
        self.assertEqual(len(resultado["fallidos"]), 2)
        mock_tx.assert_not_called()


class DetalleMovArmado1raOptTest(SimpleTestCase):
    def test_incluye_opt_en_detalle_si_id_lista(self):
        from mpr.services import _detalle_mov_armado_1ra

        det = _detalle_mov_armado_1ra(
            489, 10, [{"id_articulo": 813, "cantidad_por_pack": 1}],
            id_lista_produccion=11,
        )
        self.assertIn("OPT 11", det)
        self.assertIn("Armado OPT 11", det)

    def test_sin_opt_si_no_id_lista(self):
        from mpr.services import _detalle_mov_armado_1ra

        det = _detalle_mov_armado_1ra(
            489, 10, [{"id_articulo": 813, "cantidad_por_pack": 1}],
        )
        self.assertNotIn("OPT", det)
