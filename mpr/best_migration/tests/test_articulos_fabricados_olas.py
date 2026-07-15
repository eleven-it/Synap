"""Tests artículos terminados/fabricados, gate BOM_FABRICADO y colas stock."""

from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from mpr.best_migration.domains import domain_by_codigo, domains_required_for_orders
from mpr.best_migration.models import (
    BestArticuloMap,
    BestClienteMap,
    BestMigrationParity,
    BestStockInicialMap,
)
from mpr.best_migration.services import (
    recalcular_mapeo_articulos,
    refresh_parity_counters,
    resolver_fabricados_desde_terminados,
    resumen_stock_inicial,
    sincronizar_stock_fabricados_semi,
)

BASE = "administranet_test_fab"


class GateIgnoraBomFabricadoTests(TestCase):
    def setUp(self):
        BestMigrationParity.objects.create(base_empresa=BASE, unidades_ok=True)
        BestClienteMap.objects.create(
            base_empresa=BASE,
            best_cliente="CLI",
            best_cuit="",
            estado=BestClienteMap.Estado.VALIDADO,
            admin_codigo=1,
            validado=True,
            requerido_migracion=True,
        )
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="TERM1",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=100,
            validado=True,
            requerido_migracion=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
        )

    def test_gate_habilitado_con_fabricados_pendientes(self):
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="FAB1",
            estado=BestArticuloMap.Estado.SIN_CANDIDATO,
            requerido_migracion=False,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        parity = refresh_parity_counters(BASE)
        parity.refresh_gate()
        self.assertTrue(parity.migracion_habilitada)
        self.assertEqual(parity.articulos_total, 1)
        self.assertEqual(parity.articulos_resueltos, 1)


class RecalcularPreservaBomFabricadoTests(TestCase):
    @patch("mpr.best_migration.services.asegurar_articulos_desde_inventario")
    @patch("mpr.best_migration.services.match_open_order_skus")
    @patch("mpr.best_migration.services._fetch_best_open_skus")
    @patch("mpr.best_migration.services._load_admin_articulos")
    def test_no_borra_filas_bom_fabricado(
        self, mock_admin, mock_best, mock_match, mock_inv
    ):
        mock_best.return_value = ([], {})
        mock_admin.return_value = []
        mock_match.return_value = []
        mock_inv.return_value = {"created": 0}

        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="FAB-PRES",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=501,
            validado=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        recalcular_mapeo_articulos(BASE)
        self.assertTrue(
            BestArticuloMap.objects.filter(
                base_empresa=BASE,
                best_id_articulo="FAB-PRES",
                origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
            ).exists()
        )


class ResolverFabricadosDesdeTerminadosTests(TestCase):
    @patch("mpr.best_migration.services.match_admin_fabricados_to_best")
    @patch("mpr.best_migration.services._fetch_best_catalog_skus")
    @patch("mpr.best_migration.services._fabricado_idarts_desde_bom_terminados")
    def test_infiere_desde_bom_admin(self, mock_bom, mock_catalog, mock_match):
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="TERM-BOM",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=200,
            validado=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
        )
        mock_bom.return_value = [
            {
                "IDArt": 301,
                "id_manual": "FAB301",
                "NombreArticulo": "Tejido fabricado",
                "CodArtProv": "",
            }
        ]
        mock_catalog.return_value = ([{"id_articulo": "BEST301"}], {})
        from mpr.best_migration.article_matcher import MatchRow

        mock_match.return_value = {
            301: MatchRow(
                best_id_articulo="BEST301",
                status="INFERIDO_ALTO",
                score=95,
                admin_idart=301,
                admin_nombre="Tejido fabricado",
            )
        }

        result = resolver_fabricados_desde_terminados(BASE)
        self.assertEqual(result["fabricados_bom"], 1)
        self.assertEqual(result["created"], 1)

        fab = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="BEST301")
        self.assertEqual(
            fab.origen_requerimiento,
            BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        self.assertEqual(fab.admin_idart, 301)


class StockFabricadosSemiTests(TestCase):
    @patch("mpr.best_migration.services.refresh_parity_counters")
    @patch("mpr.best_migration.services._load_admin_stock_deposito")
    @patch("mpr.best_migration.services._fetch_best_inventario_agregado")
    def test_sync_solo_deposito_4002_fabricados(
        self, mock_inv, mock_saldos, mock_parity
    ):
        mock_parity.return_value.save = lambda: None
        mock_saldos.return_value = {}
        mock_inv.return_value = [
            {
                "id_art": "FAB-SKU",
                "articulo": "Semi fab",
                "id_dep": 4002,
                "deposito": "Semi-Embalado",
                "stock_pares": Decimal("10"),
                "docenas": None,
            },
            {
                "id_art": "OTRO",
                "articulo": "Terminado",
                "id_dep": 4003,
                "deposito": "Terminado",
                "stock_pares": Decimal("99"),
                "docenas": None,
            },
        ]
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="FAB-SKU",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=401,
            validado=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )

        sincronizar_stock_fabricados_semi(BASE)
        lineas = BestStockInicialMap.objects.filter(base_empresa=BASE)
        self.assertEqual(lineas.count(), 1)
        self.assertEqual(lineas.first().best_id_deposito, 4002)


class HubYColasStockTests(TestCase):
    def test_dominio_terminados_rename_y_fabricados_no_gate(self):
        dom_term = domain_by_codigo("articulos")
        dom_fab = domain_by_codigo("articulos_fabricados")
        self.assertEqual(dom_term.nombre, "Artículos terminados")
        self.assertEqual(dom_fab.nombre, "Artículos fabricados")
        self.assertFalse(dom_fab.obligatorio_para_pedidos)
        codes = [d.codigo for d in domains_required_for_orders()]
        self.assertIn("articulos", codes)
        self.assertNotIn("articulos_fabricados", codes)

    def test_colas_stock_inicial_por_estado(self):
        BestStockInicialMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="A1",
            best_id_deposito=1,
            estado=BestStockInicialMap.Estado.SIN_MAPEO_ARTICULO,
            requerido_migracion=True,
        )
        BestStockInicialMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="A2",
            best_id_deposito=1,
            estado=BestStockInicialMap.Estado.LISTO,
            requerido_migracion=True,
        )
        BestStockInicialMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="A3",
            best_id_deposito=1,
            estado=BestStockInicialMap.Estado.CARGADO,
            requerido_migracion=True,
        )
        res = resumen_stock_inicial(BASE)
        self.assertEqual(res["cola_pendiente_mapeo"], 1)
        self.assertEqual(res["cola_listos_carga"], 1)
        self.assertEqual(res["cola_ya_cargados"], 1)

    def test_ruta_articulos_estable(self):
        self.assertEqual(reverse("mpr:migracion_best_articulos"), "/mpr/migracion-best/articulos/")
        self.assertEqual(
            reverse("mpr:migracion_best_articulos_fabricados"),
            "/mpr/migracion-best/articulos-fabricados/",
        )
