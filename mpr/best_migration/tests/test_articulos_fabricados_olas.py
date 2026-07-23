"""Tests artículos fabricados BEST→Admin, gate BOM_FABRICADO y olas stock/pedido."""

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
    asignar_admin_a_fabricado_pp,
    buscar_fabricados_admin,
    recalcular_mapeo_articulos,
    refresh_parity_counters,
    resolver_fabricados_desde_pp_best,
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
            best_id_articulo="SEMI-PEND",
            estado=BestArticuloMap.Estado.SIN_CANDIDATO,
            requerido_migracion=True,
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
            best_id_articulo="SEMI-PRES",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=501,
            validado=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        recalcular_mapeo_articulos(BASE)
        self.assertTrue(
            BestArticuloMap.objects.filter(
                base_empresa=BASE,
                best_id_articulo="SEMI-PRES",
                origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
            ).exists()
        )


class MatcherBestPpToAdminTests(TestCase):
    def test_matcher_prioriza_id_manual_exacto(self):
        from mpr.best_migration.article_matcher import match_best_pp_to_admin_fabricados

        matches = match_best_pp_to_admin_fabricados(
            best_pps=[
                {
                    "id_articulo": "SEMI-1P",
                    "codigo": "FAB300",
                    "articulo": "Semi 1Par",
                    "marca": "MarcaX",
                }
            ],
            admin_fabricados=[
                {
                    "IDArt": 300,
                    "id_manual": "FAB300",
                    "NombreArticulo": "Componente 1Par",
                    "CodArtProv": "",
                },
                {
                    "IDArt": 301,
                    "id_manual": "OTRO",
                    "NombreArticulo": "Otro fabricado",
                    "CodArtProv": "",
                },
            ],
            myl_by_mmid={"SEMI-1P": {"CODIGO": "FAB300", "PACK": "1P"}},
        )

        self.assertEqual(matches["SEMI-1P"].admin_idart, 300)
        self.assertEqual(matches["SEMI-1P"].score, 100)

    def test_matcher_inferencia_modelo_8020(self):
        from mpr.best_migration.article_matcher import match_best_pp_to_admin_fabricados

        best_pps = [
            {
                "id_articulo": "PUMA8020RS",
                "codigo": "8020-RS",
                "articulo": "Puma 8020 Medias Rosa T3",
                "marca": "Puma",
            }
        ]
        myl = {"PUMA8020RS": {"CODIGO": "8020-RS", "COLOR": "RS", "TALLE": "3"}}
        matches = match_best_pp_to_admin_fabricados(
            best_pps=best_pps,
            admin_fabricados=[
                {
                    "IDArt": 402,
                    "id_manual": "FAB402",
                    "NombreArticulo": "8020 Rosa 1Par",
                    "CodArtProv": "",
                },
                {
                    "IDArt": 401,
                    "id_manual": "FAB401",
                    "NombreArticulo": "8020 Blanco 1Par",
                    "CodArtProv": "",
                },
            ],
            myl_by_mmid=myl,
        )

        self.assertEqual(matches["PUMA8020RS"].admin_idart, 402)
        self.assertGreater(matches["PUMA8020RS"].score or 0, 55)


class ResolverFabricadosDesdePpBestTests(TestCase):
    @patch("mpr.best_migration.services.match_best_pp_to_admin_fabricados")
    @patch("mpr.best_migration.services._load_admin_fabricados")
    @patch("mpr.best_migration.services._fetch_best_pp_ids_requeridos_pedido")
    @patch("mpr.best_migration.services._fetch_best_pp_con_stock")
    def test_infiere_desde_pp_con_stock(self, mock_stock, mock_req, mock_admin, mock_match):
        mock_stock.return_value = (
            [{"id_articulo": "SEMI-301", "codigo": "FAB301", "articulo": "Semi tejido"}],
            {"SEMI-301": {"CODIGO": "FAB301"}},
        )
        mock_req.return_value = {"SEMI-301"}
        mock_admin.return_value = [
            {
                "IDArt": 301,
                "id_manual": "FAB301",
                "NombreArticulo": "Tejido fabricado",
                "CodArtProv": "",
            }
        ]
        from mpr.best_migration.article_matcher import MatchRow

        mock_match.return_value = {
            "SEMI-301": MatchRow(
                best_id_articulo="SEMI-301",
                status="INFERIDO_ALTO",
                score=95,
                admin_idart=301,
                admin_nombre="Tejido fabricado",
            )
        }

        result = resolver_fabricados_desde_pp_best(BASE)
        self.assertEqual(result["fabricados_bom"], 1)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["pp_requeridos_pedido"], 1)

        fab = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="SEMI-301")
        self.assertEqual(
            fab.origen_requerimiento,
            BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        self.assertEqual(fab.admin_idart, 301)
        self.assertTrue(fab.requerido_migracion)
        self.assertTrue(fab.en_snapshot_abierto)

    @patch("mpr.best_migration.services.match_best_pp_to_admin_fabricados")
    @patch("mpr.best_migration.services._load_admin_fabricados")
    @patch("mpr.best_migration.services._fetch_best_pp_ids_requeridos_pedido")
    @patch("mpr.best_migration.services._fetch_best_pp_con_stock")
    def test_ola2_stock_sin_requerido_migracion(
        self, mock_stock, mock_req, mock_admin, mock_match
    ):
        mock_stock.return_value = (
            [{"id_articulo": "SEMI-STK", "codigo": "STK01", "articulo": "Semi stock"}],
            {},
        )
        mock_req.return_value = set()
        mock_admin.return_value = [
            {
                "IDArt": 310,
                "id_manual": "STK01",
                "NombreArticulo": "Fabricado stock",
                "CodArtProv": "",
            }
        ]
        from mpr.best_migration.article_matcher import MatchRow

        mock_match.return_value = {
            "SEMI-STK": MatchRow(
                best_id_articulo="SEMI-STK",
                status="INFERIDO_ALTO",
                score=100,
                admin_idart=310,
            )
        }

        resolver_fabricados_desde_pp_best(BASE)
        fab = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="SEMI-STK")
        self.assertFalse(fab.requerido_migracion)
        self.assertFalse(fab.en_snapshot_abierto)

    @patch("mpr.best_migration.services.match_best_pp_to_admin_fabricados")
    @patch("mpr.best_migration.services._load_admin_fabricados")
    @patch("mpr.best_migration.services._fetch_best_pp_ids_requeridos_pedido")
    @patch("mpr.best_migration.services._fetch_best_pp_con_stock")
    def test_no_pisa_validado(self, mock_stock, mock_req, mock_admin, mock_match):
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="SEMI-OK",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=320,
            validado=True,
            requerido_migracion=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        mock_stock.return_value = (
            [{"id_articulo": "SEMI-OK", "codigo": "X", "articulo": "Semi ok"}],
            {},
        )
        mock_req.return_value = {"SEMI-OK"}
        mock_admin.return_value = []
        mock_match.return_value = {}

        result = resolver_fabricados_desde_pp_best(BASE)
        self.assertEqual(result["preserved"], 1)
        fab = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="SEMI-OK")
        self.assertEqual(fab.estado, BestArticuloMap.Estado.VALIDADO)
        self.assertEqual(fab.admin_idart, 320)

    @patch("mpr.best_migration.services.match_best_pp_to_admin_fabricados")
    @patch("mpr.best_migration.services._load_admin_fabricados")
    @patch("mpr.best_migration.services._fetch_best_pp_ids_requeridos_pedido")
    @patch("mpr.best_migration.services._fetch_best_pp_con_stock")
    def test_usa_alternate_admin_libre(
        self, mock_stock, mock_req, mock_admin, mock_match
    ):
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="SEMI-ALT",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=330,
            validado=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        mock_stock.return_value = (
            [{"id_articulo": "SEMI-NUEVO", "codigo": "8020-RS", "articulo": "Semi rosa"}],
            {},
        )
        mock_req.return_value = {"SEMI-NUEVO"}
        mock_admin.return_value = [
            {"IDArt": 330, "id_manual": "F330", "NombreArticulo": "Ocupado", "CodArtProv": ""},
            {"IDArt": 331, "id_manual": "F331", "NombreArticulo": "Libre rosa", "CodArtProv": ""},
        ]
        from mpr.best_migration.article_matcher import MatchRow

        mock_match.return_value = {
            "SEMI-NUEVO": MatchRow(
                best_id_articulo="SEMI-NUEVO",
                status="INFERIDO_MEDIO",
                score=78,
                admin_idart=330,
                admin_nombre="Ocupado",
                extras={
                    "cand_best": [
                        {"id": 330, "articulo": "Ocupado", "score": 78},
                        {"id": 331, "articulo": "Libre rosa", "score": 76},
                    ]
                },
            )
        }

        resolver_fabricados_desde_pp_best(BASE)
        fab = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="SEMI-NUEVO")
        self.assertEqual(fab.admin_idart, 331)
        self.assertIn("alternate_libre", fab.razon)

    @patch("mpr.best_migration.services.match_best_pp_to_admin_fabricados")
    @patch("mpr.best_migration.services._load_admin_fabricados")
    @patch("mpr.best_migration.services._fetch_best_pp_ids_requeridos_pedido")
    @patch("mpr.best_migration.services._fetch_best_pp_con_stock")
    def test_sin_admin_queda_sin_candidato(
        self, mock_stock, mock_req, mock_admin, mock_match
    ):
        mock_stock.return_value = (
            [{"id_articulo": "SEMI-SIN", "codigo": "", "articulo": "Sin match"}],
            {},
        )
        mock_req.return_value = set()
        mock_admin.return_value = []
        mock_match.return_value = {}

        result = resolver_fabricados_desde_pp_best(BASE)
        fab = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="SEMI-SIN")
        self.assertEqual(fab.estado, BestArticuloMap.Estado.SIN_CANDIDATO)
        self.assertIsNone(fab.admin_idart)
        self.assertEqual(result["skipped_sin_admin"], 1)

    def test_alias_resolver_desde_terminados(self):
        with patch(
            "mpr.best_migration.services.resolver_fabricados_desde_pp_best",
            return_value={"total": 0},
        ) as mock_pp:
            resolver_fabricados_desde_terminados(BASE)
            mock_pp.assert_called_once_with(BASE)


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


class AsignarAdminAFabricadoPpTests(TestCase):
    @patch("mpr.best_migration.services._load_admin_fabricados")
    def test_asignar_valida_mapeo(self, mock_admin):
        mock_admin.return_value = [
            {
                "IDArt": 99,
                "id_manual": "FAB99",
                "NombreArticulo": "Componente 99",
                "CodArtProv": "",
            }
        ]
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="SEMI-99",
            estado=BestArticuloMap.Estado.SIN_CANDIDATO,
            best_articulo="Semi 99",
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )

        obj = asignar_admin_a_fabricado_pp(
            base_empresa=BASE,
            best_id="SEMI-99",
            nuevo_admin_idart=99,
            usuario="tester",
        )

        self.assertEqual(obj.best_id_articulo, "SEMI-99")
        self.assertEqual(obj.estado, BestArticuloMap.Estado.VALIDADO)
        self.assertTrue(obj.validado)
        self.assertEqual(obj.admin_idart, 99)

    @patch("mpr.best_migration.services._load_admin_fabricados")
    def test_conflicto_validado_otro_pp(self, mock_admin):
        mock_admin.return_value = [
            {"IDArt": 10, "id_manual": "F10", "NombreArticulo": "Fab 10", "CodArtProv": ""}
        ]
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="SEMI-A",
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart=10,
            validado=True,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="SEMI-B",
            estado=BestArticuloMap.Estado.SIN_CANDIDATO,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )

        with self.assertRaises(ValueError) as ctx:
            asignar_admin_a_fabricado_pp(
                base_empresa=BASE,
                best_id="SEMI-B",
                nuevo_admin_idart=10,
                usuario="tester",
            )
        self.assertIn("validado", str(ctx.exception).lower())

    @patch("mpr.best_migration.services._load_admin_fabricados")
    def test_reasigna_admin_no_validado(self, mock_admin):
        mock_admin.return_value = [
            {"IDArt": 20, "id_manual": "F20", "NombreArticulo": "Fab 20", "CodArtProv": ""}
        ]
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="SEMI-VIEJO",
            estado=BestArticuloMap.Estado.INFERIDO_MEDIO,
            admin_idart=20,
            validado=False,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )
        BestArticuloMap.objects.create(
            base_empresa=BASE,
            best_id_articulo="SEMI-NUEVO",
            estado=BestArticuloMap.Estado.SIN_CANDIDATO,
            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
        )

        obj = asignar_admin_a_fabricado_pp(
            base_empresa=BASE,
            best_id="SEMI-NUEVO",
            nuevo_admin_idart=20,
            usuario="tester",
        )

        self.assertEqual(obj.admin_idart, 20)
        viejo = BestArticuloMap.objects.get(base_empresa=BASE, best_id_articulo="SEMI-VIEJO")
        self.assertIsNone(viejo.admin_idart)
        self.assertEqual(viejo.estado, BestArticuloMap.Estado.SIN_CANDIDATO)


class BuscarFabricadosAdminTests(TestCase):
    @patch("mpr.best_migration.services.mysql_cursor")
    def test_busca_fabricados_admin(self, mock_cursor):
        mock_cur = mock_cursor.return_value.__enter__.return_value
        mock_cur.fetchall.return_value = [
            {
                "IDArt": 50,
                "id_manual": "F50",
                "NombreArticulo": "Tejido 50",
                "Descripcion": "Tejido 50",
                "CodArtProv": "",
            }
        ]

        results = buscar_fabricados_admin("tejido", base_empresa=BASE, limit=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["IDArt"], 50)
        mock_cur.execute.assert_called_once()
