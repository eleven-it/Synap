"""Tests unitarios del cargador de pedidos BEST → PED."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.best_migration.models import (
    BestArticuloMap,
    BestClienteMap,
    BestDepositoMap,
    BestMigrationParity,
)
from mpr.best_migration.pedido_loader import (
    _agrupar_por_orden,
    _mapear_ordenes,
    migrar_pedidos_best,
)


def _linea(
    orden: str = "100",
    cliente: str = "CLI A",
    cuit: str = "",
    id_art: str = "ART1",
    pendiente: str = "10",
) -> dict:
    return {
        "orden_nro": orden,
        "cliente": cliente,
        "cuit": cuit,
        "id_articulo": id_art,
        "codigo": "c1",
        "articulo": "Producto 1",
        "pendiente": pendiente,
        "deposito_origen": "Depósito Terminado",
        "precio": "100",
        "fecha_emision": date(2026, 7, 3),
    }


class AgruparPorOrdenTest(SimpleTestCase):
    def test_agrupa_lineas_misma_orden(self):
        lineas = [_linea(orden="200"), _linea(orden="200", id_art="ART2")]
        grupos = _agrupar_por_orden(lineas)
        self.assertEqual(len(grupos), 1)
        self.assertEqual(len(grupos["200"]), 2)


class MapearOrdenesTest(SimpleTestCase):
    def _articulo_validado(self, bid: str, idart: int = 10) -> BestArticuloMap:
        return BestArticuloMap(
            base_empresa="administranet1",
            best_id_articulo=bid,
            estado=BestArticuloMap.Estado.VALIDADO,
            validado=True,
            admin_idart=idart,
        )

    def _cliente_validado(self, nombre: str, codigo: int = 50) -> BestClienteMap:
        return BestClienteMap(
            base_empresa="administranet1",
            best_cliente=nombre,
            best_cuit="",
            estado=BestClienteMap.Estado.VALIDADO,
            validado=True,
            admin_codigo=codigo,
        )

    def test_mapea_orden_con_lineas_validas(self):
        por_orden = _agrupar_por_orden([_linea()])
        art_maps = {"ART1": self._articulo_validado("ART1")}
        cli_maps = {("CLI A", ""): self._cliente_validado("CLI A")}
        dep_maps = {"DEPOSITO TERMINADO": 3}

        migrables, omitidas, huerfanos = _mapear_ordenes(
            por_orden,
            articulo_maps=art_maps,
            cliente_maps=cli_maps,
            deposito_maps=dep_maps,
        )
        self.assertEqual(len(migrables), 1)
        self.assertEqual(len(omitidas), 0)
        self.assertEqual(len(migrables[0]["lineas"]), 1)
        self.assertEqual(migrables[0]["lineas"][0]["admin_idart"], 10)
        self.assertEqual(migrables[0]["lineas"][0]["cod_deposito"], 3)

    def test_cliente_sin_mapa_omite_pedido(self):
        por_orden = _agrupar_por_orden([_linea(cliente="SIN MAPA")])
        migrables, omitidas, huerfanos = _mapear_ordenes(
            por_orden,
            articulo_maps={"ART1": self._articulo_validado("ART1")},
            cliente_maps={},
            deposito_maps={},
        )
        self.assertEqual(len(migrables), 0)
        self.assertEqual(len(omitidas), 1)
        self.assertEqual(omitidas[0]["motivo"], "cliente_sin_mapeo")

    def test_linea_sin_articulo_es_huerfana(self):
        por_orden = _agrupar_por_orden([_linea(id_art="NOEXISTE")])
        migrables, omitidas, _ = _mapear_ordenes(
            por_orden,
            articulo_maps={},
            cliente_maps={("CLI A", ""): self._cliente_validado("CLI A")},
            deposito_maps={},
        )
        self.assertEqual(len(migrables), 0)
        self.assertEqual(omitidas[0]["motivo"], "sin_lineas_validas")


class MigrarPedidosBestTest(SimpleTestCase):
    def _parity(self, habilitada: bool) -> BestMigrationParity:
        p = BestMigrationParity(base_empresa="administranet1")
        p.migracion_habilitada = habilitada
        return p

    @patch("mpr.best_migration.pedido_loader._fetch_best_open_order_lines")
    @patch("mpr.best_migration.pedido_loader._load_deposito_maps", return_value={})
    @patch("mpr.best_migration.pedido_loader._load_cliente_maps")
    @patch("mpr.best_migration.pedido_loader._load_articulo_maps")
    @patch("mpr.best_migration.pedido_loader.refresh_parity_counters")
    def test_dry_run_cuenta_ordenes(
        self,
        mock_parity,
        mock_art,
        mock_cli,
        mock_dep,
        mock_fetch,
    ):
        mock_parity.return_value = self._parity(True)
        mock_fetch.return_value = [
            _linea(orden="100"),
            _linea(orden="100", id_art="ART2"),
            _linea(orden="200", cliente="CLI B"),
        ]
        mock_art.return_value = {
            "ART1": BestArticuloMap(
                base_empresa="administranet1",
                best_id_articulo="ART1",
                estado=BestArticuloMap.Estado.VALIDADO,
                validado=True,
                admin_idart=1,
            ),
            "ART2": BestArticuloMap(
                base_empresa="administranet1",
                best_id_articulo="ART2",
                estado=BestArticuloMap.Estado.VALIDADO,
                validado=True,
                admin_idart=2,
            ),
        }
        mock_cli.return_value = {
            ("CLI A", ""): BestClienteMap(
                base_empresa="administranet1",
                best_cliente="CLI A",
                best_cuit="",
                estado=BestClienteMap.Estado.VALIDADO,
                validado=True,
                admin_codigo=10,
            ),
        }

        result = migrar_pedidos_best("administranet1", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["gate_ok"])
        self.assertEqual(result["ordenes_leidas"], 2)
        self.assertEqual(result["ordenes_migrables"], 1)
        self.assertEqual(result["ordenes_omitidas"], 1)
        self.assertEqual(result["lineas_ok"], 2)
        self.assertEqual(result["pedidos_escritos"], 0)

    @patch("mpr.best_migration.pedido_loader.refresh_parity_counters")
    def test_gate_cerrado_bloquea_confirmar(self, mock_parity):
        mock_parity.return_value = self._parity(False)
        with self.assertRaises(ValueError) as ctx:
            migrar_pedidos_best("administranet1", dry_run=False, id_usuario=1)
        self.assertIn("Gate", str(ctx.exception))

    @patch("mpr.best_migration.pedido_loader._fetch_best_open_order_lines")
    @patch("mpr.best_migration.pedido_loader._load_deposito_maps", return_value={})
    @patch("mpr.best_migration.pedido_loader._load_cliente_maps")
    @patch("mpr.best_migration.pedido_loader._load_articulo_maps")
    @patch("mpr.best_migration.pedido_loader.refresh_parity_counters")
    def test_dry_run_gate_cerrado_avisa(
        self,
        mock_parity,
        mock_art,
        mock_cli,
        mock_dep,
        mock_fetch,
    ):
        mock_parity.return_value = self._parity(False)
        mock_fetch.return_value = []
        mock_art.return_value = {}
        mock_cli.return_value = {}

        result = migrar_pedidos_best("administranet1", dry_run=True)
        self.assertFalse(result["gate_ok"])
        self.assertTrue(any("gate cerrado" in e.lower() for e in result["errores"]))

    @patch("mpr.best_migration.pedido_loader._escribir_pedidos_mysql")
    @patch("mpr.best_migration.pedido_loader._fetch_best_open_order_lines")
    @patch("mpr.best_migration.pedido_loader._load_deposito_maps", return_value={})
    @patch("mpr.best_migration.pedido_loader._load_cliente_maps")
    @patch("mpr.best_migration.pedido_loader._load_articulo_maps")
    @patch("mpr.best_migration.pedido_loader.refresh_parity_counters")
    def test_confirmar_invoca_escritura_y_post(
        self,
        mock_parity,
        mock_art,
        mock_cli,
        mock_dep,
        mock_fetch,
        mock_escribir,
    ):
        mock_parity.return_value = self._parity(True)
        mock_fetch.return_value = [_linea()]
        mock_art.return_value = {
            "ART1": BestArticuloMap(
                base_empresa="administranet1",
                best_id_articulo="ART1",
                estado=BestArticuloMap.Estado.VALIDADO,
                validado=True,
                admin_idart=1,
            ),
        }
        mock_cli.return_value = {
            ("CLI A", ""): BestClienteMap(
                base_empresa="administranet1",
                best_cliente="CLI A",
                best_cuit="",
                estado=BestClienteMap.Estado.VALIDADO,
                validado=True,
                admin_codigo=10,
            ),
        }
        mock_escribir.return_value = (1, 0, [])

        with patch(
            "mpr.services.actualizar_pedidos_produccion", return_value=(True, "ok")
        ) as mock_post:
            result = migrar_pedidos_best(
                "administranet1", dry_run=False, id_usuario=5
            )

        mock_escribir.assert_called_once()
        mock_post.assert_called_once_with("administranet1", 5)
        self.assertEqual(result["pedidos_escritos"], 1)
        self.assertTrue(result["post_actualizar_ok"])
