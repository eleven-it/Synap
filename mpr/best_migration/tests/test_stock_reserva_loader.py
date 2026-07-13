"""Tests unitarios del cargador MCSS → articulo.stock_reserva."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.best_migration.models import BestArticuloMap
from mpr.best_migration.stock_reserva_loader import migrar_stock_reserva_best


def _best_rows(*pairs: tuple[str, str]) -> list[dict]:
    return [{"best_id": bid, "mcss": Decimal(val)} for bid, val in pairs]


class MigrarStockReservaBestTest(SimpleTestCase):
    def _articulo_map(self, bid: str, idart: int) -> MagicMock:
        m = MagicMock()
        m.best_id_articulo = bid
        m.admin_idart = idart
        return m

    @patch("mpr.best_migration.stock_reserva_loader._leer_stock_reserva_actual")
    @patch("mpr.best_migration.stock_reserva_loader._cargar_mapa_articulos")
    @patch("mpr.best_migration.stock_reserva_loader.connect_best")
    @patch("mpr.best_migration.stock_reserva_loader.fetch_dict")
    def test_dry_run_cuenta_mapeados_y_huerfanos(
        self, mock_fetch, mock_connect, mock_mapa, mock_actuales
    ):
        mock_connect.return_value = MagicMock()
        mock_fetch.return_value = _best_rows(
            ("1001", "50"),
            ("1002", "30"),
            ("9999", "100"),
        )
        mock_mapa.return_value = {"1001": 10, "1002": 20}
        mock_actuales.return_value = {10: Decimal("50"), 20: Decimal("0")}

        result = migrar_stock_reserva_best("administranet1", dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["leidos"], 3)
        self.assertEqual(result["con_mcss"], 3)
        self.assertEqual(result["mapeados"], 2)
        self.assertEqual(result["huerfanos"], 1)
        self.assertEqual(result["actualizados"], 1)
        self.assertEqual(result["sin_cambio"], 1)
        self.assertEqual(len(result["huerfanos_muestra"]), 1)
        self.assertEqual(result["huerfanos_muestra"][0]["best_id"], "9999")

    @patch("mpr.best_migration.stock_reserva_loader._leer_stock_reserva_actual")
    @patch("mpr.best_migration.stock_reserva_loader._cargar_mapa_articulos")
    @patch("mpr.best_migration.stock_reserva_loader.connect_best")
    @patch("mpr.best_migration.stock_reserva_loader.fetch_dict")
    def test_ignora_mcss_cero_sin_incluir_ceros(
        self, mock_fetch, mock_connect, mock_mapa, mock_actuales
    ):
        mock_connect.return_value = MagicMock()
        mock_fetch.return_value = _best_rows(("1001", "0"), ("1002", "10"))
        mock_mapa.return_value = {"1001": 10, "1002": 20}
        mock_actuales.return_value = {20: Decimal("0")}

        result = migrar_stock_reserva_best("administranet1", dry_run=True)

        self.assertEqual(result["mapeados"], 1)
        self.assertEqual(result["actualizados"], 1)

    @patch("mpr.best_migration.stock_reserva_loader.mysql_cursor")
    @patch("mpr.best_migration.stock_reserva_loader._verificar_columna_stock_reserva")
    @patch("mpr.best_migration.stock_reserva_loader._leer_stock_reserva_actual")
    @patch("mpr.best_migration.stock_reserva_loader._cargar_mapa_articulos")
    @patch("mpr.best_migration.stock_reserva_loader.connect_best")
    @patch("mpr.best_migration.stock_reserva_loader.fetch_dict")
    def test_confirm_escribe_y_post_actualiza(
        self,
        mock_fetch,
        mock_connect,
        mock_mapa,
        mock_actuales,
        mock_verificar,
        mock_mysql,
    ):
        mock_connect.return_value = MagicMock()
        mock_fetch.return_value = _best_rows(("1001", "25"))
        mock_mapa.return_value = {"1001": 10}
        mock_actuales.return_value = {10: Decimal("0")}

        mock_cur = MagicMock()
        mock_cur.rowcount = 1
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_cur)
        mock_cm.__exit__ = MagicMock(return_value=False)
        mock_mysql.return_value = mock_cm

        with patch(
            "mpr.services.actualizar_pedidos_produccion", return_value=(True, "OK")
        ) as mock_post:
            result = migrar_stock_reserva_best(
                "administranet1",
                dry_run=False,
                id_usuario=1,
            )

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["actualizados"], 1)
        mock_cur.execute.assert_called_once()
        mock_post.assert_called_once_with("administranet1", 1)
        self.assertTrue(result["post_actualizar_ok"])
