"""Tests borrador, fecha y catálogo Terminado en armado."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import (
    ESTADO_ARMADO_BORRADOR,
    TIPO_ART_FAB_TERMINADO,
    ejecutar_lote_armado,
    parse_cabecera_lote_armado_surtido,
)


class ParseCabeceraArmadoTest(SimpleTestCase):
    def test_fecha_ddmmyyyy_y_accion(self):
        cab = parse_cabecera_lote_armado_surtido({
            "deposito_origen": "3",
            "deposito_destino": "5",
            "accion": "borrador",
            "fecha_realizado": "15/03/2026",
            "id_mpr_armado_lote": "42",
        })
        self.assertEqual(cab["accion"], "borrador")
        self.assertEqual(cab["fecha_realizado"], date(2026, 3, 15))
        self.assertEqual(cab["id_mpr_armado_lote"], 42)

    def test_fecha_iso_y_default_aprobar(self):
        cab = parse_cabecera_lote_armado_surtido({
            "fecha_realizado": "2026-03-15",
        })
        self.assertEqual(cab["accion"], "aprobar")
        self.assertEqual(cab["fecha_realizado"], date(2026, 3, 15))


class EjecutarLoteBorradorTest(SimpleTestCase):
    def _cab(self):
        return {
            "modo": "2da",
            "accion": "borrador",
            "deposito_origen": 3,
            "deposito_destino": 5,
            "id_operario": 10,
            "fecha_realizado": date(2026, 1, 10),
        }

    def _items(self):
        return [{
            "id_articulo_pack": 100,
            "cantidad_packs": 2,
            "lineas": [{"id_articulo": 813, "cantidad_por_pack": 1}],
        }]

    @patch("mpr.services.validar_reglas_lote_armado", return_value=(True, None))
    @patch("mpr.repositories.armado_surtido.reemplazar_items_lote")
    @patch("mpr.repositories.armado_surtido.actualizar_lote_armado")
    @patch("mpr.repositories.armado_surtido.crear_lote_armado")
    @patch("mpr.repositories.ledger_backend.mpr_writes_mysql", return_value=True)
    @patch("mpr.repositories.ledger_backend.mpr_writes_postgres", return_value=False)
    @patch("mpr.services._ejecutar_armado_surtido_tx")
    def test_borrador_no_llama_stock_tx(
        self, mock_tx, _mock_pg, _mock_mysql, mock_crear, *_rest,
    ):
        lote_mock = MagicMock()
        lote_mock.id_mpr_armado_lote = 7
        lote_mock.id = "uuid-7"
        lote_mock.uuid_lote = "uuid-7"
        mock_crear.return_value = lote_mock

        resultado = ejecutar_lote_armado("emp", 1, self._cab(), self._items())

        mock_tx.assert_not_called()
        self.assertEqual(resultado["estado"], ESTADO_ARMADO_BORRADOR)
        self.assertEqual(resultado["exitosos"], [])
        self.assertEqual(resultado["id_lote_armado"], "uuid-7")

    @patch("mpr.services.guardar_composicion_armado_surtido")
    @patch("mpr.services._ejecutar_items_lote_armado_stock")
    @patch("mpr.services.validar_reglas_lote_armado", return_value=(True, None))
    @patch("mpr.repositories.armado_surtido.reemplazar_items_lote")
    @patch("mpr.repositories.armado_surtido.actualizar_lote_armado")
    @patch("mpr.repositories.armado_surtido.crear_lote_armado")
    @patch("mpr.repositories.ledger_backend.mpr_writes_mysql", return_value=True)
    @patch("mpr.repositories.ledger_backend.mpr_writes_postgres", return_value=False)
    def test_aprobar_pasa_fecha_a_ejecucion(
        self, _mock_pg, _mock_mysql, mock_crear, mock_upd, mock_reempl, mock_val, mock_exec_items, *_m,
    ):
        lote_mock = MagicMock()
        lote_mock.id_mpr_armado_lote = 8
        lote_mock.id = "uuid-8"
        lote_mock.uuid_lote = "uuid-8"
        mock_crear.return_value = lote_mock
        mock_exec_items.return_value = {"exitosos": [{"id_articulo_pack": 100}], "fallidos": []}

        cab = dict(self._cab())
        cab["accion"] = "aprobar"
        ejecutar_lote_armado("emp", 1, cab, self._items())

        mock_exec_items.assert_called_once()
        args = mock_exec_items.call_args[0]
        self.assertEqual(args[6], date(2026, 1, 10))


class TerminadoCatalogoConstantTest(SimpleTestCase):
    def test_constante_terminado(self):
        self.assertEqual(TIPO_ART_FAB_TERMINADO, "Terminado")
