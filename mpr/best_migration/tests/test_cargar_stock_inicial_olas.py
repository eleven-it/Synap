"""Tests de stock inicial BEST por olas (guardrails sync + saldo live)."""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from mpr.best_migration.models import (
    BestArticuloMap,
    BestDepositoMap,
    BestStockInicialMap,
)
from mpr.best_migration.services import (
    cargar_stock_inicial_best,
    sincronizar_stock_inicial,
)

BASE = "administranet_test_olas"


def _crear_linea(
    *,
    best_id_articulo: str = "ART1",
    best_id_deposito: int = 10,
    best_stock_pares: Decimal = Decimal("100"),
    admin_idart: int = 101,
    admin_cod_deposito: int = 5,
    admin_saldo_actual: Decimal | None = Decimal("0"),
    estado: str = BestStockInicialMap.Estado.LISTO,
    notas: str = "",
) -> BestStockInicialMap:
    delta = None
    if admin_saldo_actual is not None:
        delta = best_stock_pares - admin_saldo_actual
    return BestStockInicialMap.objects.create(
        base_empresa=BASE,
        best_id_articulo=best_id_articulo,
        best_articulo="Artículo prueba",
        best_id_deposito=best_id_deposito,
        best_deposito_nombre="Dep prueba",
        best_stock_pares=best_stock_pares,
        admin_idart=admin_idart,
        admin_nombre="Admin art",
        admin_cod_deposito=admin_cod_deposito,
        admin_deposito_nombre="Dep admin",
        admin_saldo_actual=admin_saldo_actual,
        delta_pares=delta,
        estado=estado,
        requerido_migracion=True,
        notas=notas,
    )


def _mock_saldos_live(**pares: Decimal) -> dict[tuple[int, int], Decimal]:
    """Claves: 'idart_iddep' → saldo, ej. '101_5' → Decimal('0')."""
    out: dict[tuple[int, int], Decimal] = {}
    for clave, saldo in pares.items():
        id_art, id_dep = clave.split("_")
        out[(int(id_art), int(id_dep))] = saldo
    return out


class CargarStockInicialOla1Tests(TestCase):
    @patch("mpr.best_migration.services.refresh_parity_counters")
    @patch("mpr.best_migration.services._load_admin_articulos_para_stock")
    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("mpr.best_migration.services._load_admin_stock_deposito")
    @patch("mpr.best_migration.services.sincronizar_stock_inicial")
    def test_ola1_listo_confirmado_cargado_y_alta_movimiento(
        self,
        mock_sync,
        mock_saldos,
        mock_alta,
        mock_articulos,
        mock_parity,
    ):
        mock_sync.return_value = {"total": 1}
        mock_saldos.return_value = _mock_saldos_live(**{"101_5": Decimal("0")})
        mock_articulos.return_value = {
            101: {"codigo_articulo": "COD1", "nombre_articulo": "Art 1"},
        }
        mock_alta.return_value = (True, 9001, "SI-001", "", [])
        mock_parity.return_value.save = lambda: None

        linea = _crear_linea()

        result = cargar_stock_inicial_best(
            BASE,
            dry_run=False,
            usuario="tester",
            id_usuario=1,
            id_puesto=1,
        )

        self.assertTrue(result["sincronizado_previo"])
        self.assertEqual(result["escrituras"], 1)
        self.assertEqual(result["ya_cargados_preservados"], 0)
        mock_alta.assert_called_once()

        linea.refresh_from_db()
        self.assertEqual(linea.estado, BestStockInicialMap.Estado.CARGADO)
        self.assertIn("MSTOCK", linea.notas)


class CargarStockInicialOla2Tests(TestCase):
    @patch("mpr.best_migration.services.refresh_parity_counters")
    @patch("mpr.best_migration.services._load_admin_articulos_para_stock")
    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("mpr.best_migration.services._load_admin_stock_deposito")
    @patch("mpr.best_migration.services.sincronizar_stock_inicial")
    def test_ola2_solo_nueva_linea_candidata(
        self,
        mock_sync,
        mock_saldos,
        mock_alta,
        mock_articulos,
        mock_parity,
    ):
        mock_sync.return_value = {"total": 2}
        mock_saldos.return_value = _mock_saldos_live(
            **{"101_5": Decimal("100"), "102_5": Decimal("0")}
        )
        mock_articulos.return_value = {
            102: {"codigo_articulo": "COD2", "nombre_articulo": "Art 2"},
        }
        mock_alta.return_value = (True, 9002, "SI-002", "", [])
        mock_parity.return_value.save = lambda: None

        prev = _crear_linea(
            best_id_articulo="ART1",
            admin_idart=101,
            estado=BestStockInicialMap.Estado.CARGADO,
            notas="MSTOCK ola 1",
        )
        nueva = _crear_linea(
            best_id_articulo="ART2",
            admin_idart=102,
            best_stock_pares=Decimal("50"),
        )

        result = cargar_stock_inicial_best(
            BASE,
            dry_run=False,
            usuario="tester",
            id_usuario=1,
        )

        self.assertEqual(result["candidatos"], 1)
        self.assertEqual(result["escrituras"], 1)
        self.assertEqual(result["ya_cargados_preservados"], 1)
        mock_alta.assert_called_once()

        prev.refresh_from_db()
        nueva.refresh_from_db()
        self.assertEqual(prev.estado, BestStockInicialMap.Estado.CARGADO)
        self.assertEqual(prev.notas, "MSTOCK ola 1")
        self.assertEqual(nueva.estado, BestStockInicialMap.Estado.CARGADO)
        self.assertIn("MSTOCK", nueva.notas)


class CargarStockInicialReconfirmarTests(TestCase):
    @patch("mpr.best_migration.services.refresh_parity_counters")
    @patch("mpr.best_migration.services._load_admin_articulos_para_stock")
    @patch("core.services.administranet_stock.alta_movimiento")
    @patch("mpr.best_migration.services._load_admin_stock_deposito")
    @patch("mpr.best_migration.services.sincronizar_stock_inicial")
    def test_reconfirmar_admin_igual_best_sin_escrituras(
        self,
        mock_sync,
        mock_saldos,
        mock_alta,
        mock_articulos,
        mock_parity,
    ):
        mock_sync.return_value = {"total": 1}
        mock_articulos.return_value = {}
        # Snapshot viejo con delta>0; live ya igualó BEST.
        mock_saldos.return_value = _mock_saldos_live(**{"101_5": Decimal("100")})
        mock_parity.return_value.save = lambda: None

        linea = _crear_linea(
            best_stock_pares=Decimal("100"),
            admin_saldo_actual=Decimal("0"),
        )

        result = cargar_stock_inicial_best(
            BASE,
            dry_run=False,
            usuario="tester",
            id_usuario=1,
        )

        self.assertEqual(result["escrituras"], 0)
        self.assertEqual(result["omitidos_admin_ge_best"], 1)
        mock_alta.assert_not_called()

        linea.refresh_from_db()
        self.assertEqual(linea.estado, BestStockInicialMap.Estado.CARGADO)
        self.assertEqual(linea.admin_saldo_actual, Decimal("100"))
        self.assertEqual(linea.delta_pares, Decimal("0"))
        self.assertIn("Sin movimiento", linea.notas)


class SincronizarStockPreservaCargadoTests(TestCase):
    @patch("mpr.best_migration.services.refresh_parity_counters")
    @patch("mpr.best_migration.services._load_admin_stock_deposito")
    @patch("mpr.best_migration.services._fetch_best_inventario_agregado")
    @patch("mpr.best_migration.services.asegurar_articulos_desde_inventario")
    def test_sync_no_reabre_cargado(
        self,
        mock_asegurar,
        mock_inv,
        mock_saldos,
        mock_parity,
    ):
        mock_asegurar.return_value = {}
        mock_saldos.return_value = _mock_saldos_live(**{"101_5": Decimal("100")})
        mock_parity.return_value.save = lambda: None

        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="ART1",
            admin_idart=101,
            admin_nombre="Art admin",
            estado=BestArticuloMap.Estado.VALIDADO,
        )
        BestDepositoMap.objects.create(
            base_empresa=BASE,
            best_id_deposito=10,
            admin_cod_deposito=5,
            admin_nombre="Dep admin",
            estado=BestDepositoMap.Estado.VALIDADO,
        )

        cargado = _crear_linea(
            best_stock_pares=Decimal("100"),
            admin_saldo_actual=Decimal("100"),
            estado=BestStockInicialMap.Estado.CARGADO,
            notas="MSTOCK 999 preservado",
        )

        mock_inv.return_value = [
            {
                "id_art": "ART1",
                "id_dep": 10,
                "stock_pares": Decimal("200"),
                "articulo": "Art BEST nuevo",
                "deposito": "Dep BEST",
                "docenas": None,
            }
        ]

        sincronizar_stock_inicial(BASE)

        cargado.refresh_from_db()
        self.assertEqual(cargado.estado, BestStockInicialMap.Estado.CARGADO)
        self.assertEqual(cargado.best_stock_pares, Decimal("100"))
        self.assertEqual(cargado.notas, "MSTOCK 999 preservado")
