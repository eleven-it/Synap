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
    asignar_best_a_fabricado,
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
    def test_matcher_prioriza_id_manual_exacto_y_pack_un_par(self):
        from mpr.best_migration.article_matcher import match_admin_fabricados_to_best

        matches = match_admin_fabricados_to_best(
            admin_fabricados=[
                {
                    "IDArt": 300,
                    "id_manual": "FAB300",
                    "NombreArticulo": "Componente 1Par",
                    "CodArtProv": "",
                }
            ],
            best_rows=[
                {"id_articulo": "SEMI-OTRO", "codigo": "FAB300", "articulo": "Otro"},
                {"id_articulo": "SEMI-1P", "codigo": "OTRO", "articulo": "Semi"},
            ],
            myl_by_mmid={
                "SEMI-OTRO": {"CODIGO": "FAB300", "PACK": "3P"},
                "SEMI-1P": {"CODIGO": "FAB300", "PACK": "1P"},
            },
        )

        self.assertEqual(matches[300].best_id_articulo, "SEMI-1P")
        self.assertEqual(matches[300].score, 100)

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

    @patch("mpr.best_migration.services.match_admin_fabricados_to_best")
    @patch("mpr.best_migration.services._fetch_best_catalog_skus")
    @patch("mpr.best_migration.services._fabricado_idarts_desde_bom_terminados")
    def test_no_pisa_mapeo_pedido_abierto_con_sku_inferido(
        self, mock_bom, mock_catalog, mock_match
    ):
        from mpr.best_migration.article_matcher import MatchRow

        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="PT-4003",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=200,
            validado=True,
            requerido_migracion=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
        )
        mock_bom.return_value = [
            {
                "IDArt": 302,
                "id_manual": "FAB302",
                "NombreArticulo": "Componente fabricado",
                "CodArtProv": "",
            }
        ]
        # El mock del catálogo representa solo Semi/Producción, no PT 4003.
        mock_catalog.return_value = ([{"id_articulo": "SEMI-4002"}], {})
        mock_match.return_value = {
            302: MatchRow(
                best_id_articulo="PT-4003",
                status="INFERIDO_ALTO",
                score=95,
                admin_idart=302,
            )
        }

        resolver_fabricados_desde_terminados(BASE)

        terminado = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="PT-4003")
        self.assertEqual(
            terminado.origen_requerimiento,
            BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
        )
        fabricado = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="FAB:302")
        self.assertEqual(
            fabricado.origen_requerimiento,
            BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        self.assertEqual(fabricado.estado, BestArticuloMap.Estado.SIN_CANDIDATO)

    @patch("mpr.best_migration.services.match_admin_fabricados_to_best")
    @patch("mpr.best_migration.services._fetch_best_catalog_skus")
    @patch("mpr.best_migration.services._fabricado_idarts_desde_bom_terminados")
    def test_crea_clave_fab_cuando_no_hay_match(
        self, mock_bom, mock_catalog, mock_match
    ):
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
                "IDArt": 303,
                "id_manual": "FAB303",
                "NombreArticulo": "Componente sin SKU",
                "CodArtProv": "",
            }
        ]
        mock_catalog.return_value = ([], {})
        mock_match.return_value = {}

        result = resolver_fabricados_desde_terminados(BASE)

        fabricado = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="FAB:303")
        self.assertEqual(fabricado.estado, BestArticuloMap.Estado.SIN_CANDIDATO)
        self.assertEqual(fabricado.best_articulo, "Componente sin SKU")
        self.assertEqual(result["skipped_sin_best"], 1)


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
        self.assertEqual(
            reverse("mpr:migracion_best_api_skus_componentes"),
            "/mpr/migracion-best/api/skus-componentes/",
        )


class AsignarBestAFabricadoTests(TestCase):
    @patch("mpr.best_migration.services._fetch_best_catalog_skus")
    def test_asignar_reemplaza_fab_y_valida(self, mock_catalog):
        mock_catalog.return_value = (
            [
                {
                    "id_articulo": "SEMI-99",
                    "codigo": "FAB99",
                    "articulo": "Tejido semi",
                    "marca": "MarcaX",
                }
            ],
            {},
        )
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="FAB:99",
            estado=BestArticuloMap.Estado.SIN_CANDIDATO,
            admin_idart=99,
            admin_nombre="Componente 99",
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )

        obj = asignar_best_a_fabricado(
            base_empresa=BASE,
            map_best_id="FAB:99",
            nuevo_best_id="SEMI-99",
            usuario="tester",
        )

        self.assertEqual(obj.best_id_articulo, "SEMI-99")
        self.assertEqual(obj.estado, BestArticuloMap.Estado.VALIDADO)
        self.assertTrue(obj.validado)
        self.assertEqual(obj.admin_idart, 99)
        self.assertEqual(obj.best_codigo, "FAB99")
        self.assertEqual(obj.best_articulo, "Tejido semi")
        self.assertFalse(
            BestArticuloMap.objects.filter(
                base_empresa=BASE, best_id_articulo="FAB:99"
            ).exists()
        )

    def test_conflicto_con_pedido_abierto(self):
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="PT-OCUPADO",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=10,
            validado=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
        )
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="FAB:20",
            estado=BestArticuloMap.Estado.SIN_CANDIDATO,
            admin_idart=20,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )

        with self.assertRaises(ValueError) as ctx:
            asignar_best_a_fabricado(
                base_empresa=BASE,
                map_best_id="FAB:20",
                nuevo_best_id="PT-OCUPADO",
                usuario="tester",
            )
        self.assertIn("Pedido abierto", str(ctx.exception))
        fab = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="FAB:20")
        self.assertEqual(fab.estado, BestArticuloMap.Estado.SIN_CANDIDATO)
