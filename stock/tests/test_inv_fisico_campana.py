# -*- coding: utf-8 -*-
"""Tests campaña inventario físico (Fase 2 — Strict TDD)."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.urls import reverse

from stock.services import inventario_fisico as svc


class TiposMprElegiblesTest(SimpleTestCase):
    def test_tipos_mpr_elegibles_por_ambito(self):
        for tipo in ("Terminado", "2daSeleccion", "Produccion", "SemiElaborado"):
            self.assertTrue(svc.es_tipo_mpr_elegible(tipo))

    def test_tipos_mpr_no_elegibles(self):
        for tipo in ("MateriaPrima", "Otro", "", None):
            self.assertFalse(svc.es_tipo_mpr_elegible(tipo))

    def test_ambito_de_tipo_mpr(self):
        self.assertEqual(svc.ambito_de_tipo_mpr("Terminado"), svc.AMBITO_TERMINADOS)
        self.assertEqual(svc.ambito_de_tipo_mpr("2daSeleccion"), svc.AMBITO_TERMINADOS)
        self.assertEqual(svc.ambito_de_tipo_mpr("Produccion"), svc.AMBITO_FABRICADOS)
        self.assertEqual(svc.ambito_de_tipo_mpr("SemiElaborado"), svc.AMBITO_FABRICADOS)
        self.assertIsNone(svc.ambito_de_tipo_mpr("MateriaPrima"))


class TiposArtFabElegiblesTest(SimpleTestCase):
    def test_terminados_acepta_terminado_y_tercero(self):
        for tipo in ("Terminado", "Tercero"):
            self.assertTrue(
                svc.es_tipo_art_fab_elegible(tipo, ambito=svc.AMBITO_TERMINADOS)
            )

    def test_fabricados_acepta_solo_fabricado(self):
        self.assertTrue(
            svc.es_tipo_art_fab_elegible("Fabricado", ambito=svc.AMBITO_FABRICADOS)
        )
        self.assertFalse(
            svc.es_tipo_art_fab_elegible("Tercero", ambito=svc.AMBITO_FABRICADOS)
        )

    def test_fabricado_2da_no_es_elegible(self):
        self.assertFalse(svc.es_tipo_art_fab_elegible("Fabricado 2da"))
        self.assertFalse(
            svc.es_tipo_art_fab_elegible("Fabricado 2da", ambito=svc.AMBITO_TERMINADOS)
        )
        self.assertFalse(
            svc.es_tipo_art_fab_elegible("Fabricado 2da", ambito=svc.AMBITO_FABRICADOS)
        )

    def test_union_generica_sin_fabricado_2da(self):
        for tipo in ("Terminado", "Tercero", "Fabricado"):
            self.assertTrue(svc.es_tipo_art_fab_elegible(tipo))
        self.assertFalse(svc.es_tipo_art_fab_elegible(""))

    def test_tipos_art_fab_por_tipo_mpr_deposito(self):
        self.assertEqual(
            svc.tipos_art_fab_para_tipo_mpr("Terminado"),
            svc.TIPOS_ART_FAB_POR_AMBITO[svc.AMBITO_TERMINADOS],
        )
        self.assertEqual(
            svc.tipos_art_fab_para_tipo_mpr("Produccion"),
            svc.TIPOS_ART_FAB_POR_AMBITO[svc.AMBITO_FABRICADOS],
        )

    def test_sql_filtro_tipo_art_fab_incluye_placeholders(self):
        sql, params = svc._sql_filtro_tipo_art_fab("a")
        self.assertIn("COALESCE(TRIM(a.tipo_art_fab), '') IN", sql)
        self.assertEqual(set(params), set(svc.TIPOS_ART_FAB_ELEGIBLES))
        self.assertNotIn("Fabricado 2da", params)

    def test_sql_filtro_art_por_ambito_deposito(self):
        sql, params = svc._sql_filtro_art_por_ambito_deposito("a", "dep")
        self.assertIn("dep.tipo_mpr", sql)
        self.assertIn("a.tipo_art_fab", sql)
        self.assertIn("Terminado", params)
        self.assertIn("Fabricado", params)
        self.assertNotIn("Fabricado 2da", params)


class CalcularDiferenciaTest(SimpleTestCase):
    def test_diferencia_positiva_sobrante(self):
        self.assertEqual(svc.calcular_diferencia(Decimal("15"), Decimal("10")), Decimal("5"))

    def test_diferencia_negativa_faltante(self):
        self.assertEqual(svc.calcular_diferencia(Decimal("8"), Decimal("12")), Decimal("-4"))

    def test_contado_none_es_cero(self):
        self.assertEqual(svc.calcular_diferencia(None, Decimal("3")), Decimal("-3"))


class TransicionesEstadoTest(SimpleTestCase):
    def test_borrador_a_en_conteo(self):
        self.assertTrue(svc.transicion_estado_permitida(svc.ESTADO_BORRADOR, svc.ESTADO_EN_CONTEO))

    def test_borrador_no_a_aplicado(self):
        self.assertFalse(svc.transicion_estado_permitida(svc.ESTADO_BORRADOR, svc.ESTADO_APLICADO))

    def test_en_conteo_a_en_revision(self):
        self.assertTrue(svc.transicion_estado_permitida(svc.ESTADO_EN_CONTEO, svc.ESTADO_EN_REVISION))

    def test_en_revision_reconteo_a_en_conteo(self):
        self.assertTrue(svc.transicion_estado_permitida(svc.ESTADO_EN_REVISION, svc.ESTADO_EN_CONTEO))

    def test_aplicado_es_terminal(self):
        self.assertFalse(svc.transicion_estado_permitida(svc.ESTADO_APLICADO, svc.ESTADO_ANULADO))


class AsignacionContadoresTest(SimpleTestCase):
    def test_usuario_asignado_puede_contar(self):
        campana = {"contadores_json": json.dumps([10, 20])}
        self.assertTrue(svc.usuario_asignado_a_campana(campana, 10))

    def test_usuario_no_asignado_bloqueado(self):
        campana = {"contadores_json": json.dumps([10])}
        self.assertFalse(svc.usuario_asignado_a_campana(campana, 99))


class ParseIdsContadoresTest(SimpleTestCase):
    def test_lista_post_normaliza_a_ints_unicos(self):
        self.assertEqual(svc.parse_ids_contadores(["10", "20", "10"]), [10, 20])

    def test_string_csv_y_espacios(self):
        self.assertEqual(svc.parse_ids_contadores("10, 24; 37\n24"), [10, 24, 37])

    def test_descarta_no_numericos_y_none(self):
        self.assertEqual(svc.parse_ids_contadores(["a", "", None, "5"]), [5])

    def test_vacio_devuelve_lista_vacia(self):
        self.assertEqual(svc.parse_ids_contadores(None), [])
        self.assertEqual(svc.parse_ids_contadores([]), [])


class EtiquetarContadoresTest(SimpleTestCase):
    CANDIDATOS = [
        {"id_usuario": 10, "cod_usuario": "JPEREZ", "nombre_completo": "Juan Pérez"},
        {"id_usuario": 20, "cod_usuario": "", "nombre_completo": "Ana Gómez"},
    ]

    def test_etiqueta_codigo_y_nombre(self):
        det = svc.etiquetar_contadores([10], self.CANDIDATOS)
        self.assertEqual(det, [{"id_usuario": 10, "etiqueta": "JPEREZ · Juan Pérez"}])

    def test_etiqueta_solo_nombre_si_sin_codigo(self):
        det = svc.etiquetar_contadores([20], self.CANDIDATOS)
        self.assertEqual(det[0]["etiqueta"], "Ana Gómez")

    def test_id_desconocido_usa_fallback(self):
        det = svc.etiquetar_contadores([99], self.CANDIDATOS)
        self.assertEqual(det[0]["etiqueta"], "Usuario #99")


class CrearCampanaServiceTest(SimpleTestCase):
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_crear_campana_rechaza_deposito_no_mpr(self, mock_cursor_ctx):
        cursor = MagicMock()
        tablas = [{"Tables_in_x": "deposito"}]
        cursor.fetchall.return_value = tablas
        cursor.fetchone.return_value = {
            "CodDeposito": 5,
            "tipo_mpr": "MateriaPrima",
            "suma_stock": "Si",
        }
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.crear_campana(
            "empresa_test",
            fecha="2026-07-23",
            depositos_ids=[5],
            id_usuario_alta=1,
        )
        self.assertFalse(ok)
        self.assertIn("elegible", result.get("error", "").lower())

    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_crear_campana_rechaza_mezcla_ambitos(self, mock_cursor_ctx):
        cursor = MagicMock()
        tablas = [{"Tables_in_x": "deposito"}]
        cursor.fetchall.return_value = tablas
        cursor.fetchone.side_effect = [
            {"CodDeposito": 3, "tipo_mpr": "Terminado", "suma_stock": "Si"},
            {"CodDeposito": 7, "tipo_mpr": "Produccion", "suma_stock": "Si"},
        ]
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.crear_campana(
            "empresa_test",
            fecha="2026-07-23",
            depositos_ids=[3, 7],
            id_usuario_alta=1,
        )
        self.assertFalse(ok)
        self.assertEqual(result.get("error"), svc.ERROR_MEZCLA_AMBITOS)

    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_crear_campana_inserta_lineas_snapshot_terminados(self, mock_cursor_ctx):
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "CodDeposito": 3,
            "tipo_mpr": "Terminado",
            "suma_stock": "Si",
        }
        cursor.lastrowid = 42
        tablas = [
            {"Tables_in_x": "deposito"},
            {"Tables_in_x": "stock_deposito"},
            {"Tables_in_x": "articulo"},
        ]
        cursor.fetchall.side_effect = [
            tablas,
            tablas,
            tablas,
            [{"id_articulo": 100, "saldo": Decimal("7.0000")}],
        ]
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.crear_campana(
            "empresa_test",
            fecha="2026-07-23",
            depositos_ids=[3],
            id_usuario_alta=7,
        )
        self.assertTrue(ok, result)
        self.assertEqual(result["id_campana"], 42)
        self.assertEqual(result["estado"], svc.ESTADO_BORRADOR)
        inserts = [c.args[0] for c in cursor.execute.call_args_list if c.args]
        linea_inserts = [s for s in inserts if "inv_fisico_linea" in s and "INSERT" in s.upper()]
        self.assertEqual(len(linea_inserts), 1)
        self.assertIn("saldo_snapshot", linea_inserts[0])
        snapshot_sql = [
            s for s in inserts if "stock_deposito" in s.lower() and "inner join" in s.lower()
        ]
        self.assertEqual(len(snapshot_sql), 1)
        self.assertIn("tipo_art_fab", snapshot_sql[0].lower())
        snapshot_args = next(
            c.args[1]
            for c in cursor.execute.call_args_list
            if c.args and "stock_deposito" in c.args[0].lower() and "inner join" in c.args[0].lower()
        )
        tipos_terminados = svc.TIPOS_ART_FAB_POR_AMBITO[svc.AMBITO_TERMINADOS]
        self.assertEqual(set(snapshot_args[1:]), set(tipos_terminados))

    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_crear_campana_inserta_lineas_snapshot_fabricados(self, mock_cursor_ctx):
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "CodDeposito": 8,
            "tipo_mpr": "SemiElaborado",
            "suma_stock": "Si",
        }
        cursor.lastrowid = 55
        tablas = [
            {"Tables_in_x": "deposito"},
            {"Tables_in_x": "stock_deposito"},
            {"Tables_in_x": "articulo"},
        ]
        cursor.fetchall.side_effect = [
            tablas,
            tablas,
            tablas,
            [{"id_articulo": 200, "saldo": Decimal("3")}],
        ]
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)

        ok, result = svc.crear_campana(
            "empresa_test",
            fecha="2026-07-23",
            depositos_ids=[8],
            id_usuario_alta=7,
        )
        self.assertTrue(ok, result)
        snapshot_args = next(
            c.args[1]
            for c in cursor.execute.call_args_list
            if c.args and "stock_deposito" in c.args[0].lower() and "inner join" in c.args[0].lower()
        )
        self.assertEqual(
            set(snapshot_args[1:]),
            set(svc.TIPOS_ART_FAB_POR_AMBITO[svc.AMBITO_FABRICADOS]),
        )


class InventarioPivoteIntactoTest(SimpleTestCase):
    """2.4 — consulta pivote /stock/inventario/ no se confunde con inventario físico."""

    def test_reverse_inventario_consulta_pivote_existe(self):
        self.assertEqual(reverse("stock:inventario"), "/stock/inventario/")

    def test_reverse_inventario_fisico_es_ruta_distinta(self):
        self.assertEqual(reverse("stock:inventario_fisico_list"), "/stock/inventario-fisico/")
        self.assertNotEqual(reverse("stock:inventario"), reverse("stock:inventario_fisico_list"))

    def test_nombres_url_distinguen_consulta_y_fisico(self):
        self.assertIn("inventario-fisico", reverse("stock:inventario_fisico_list"))
        self.assertNotIn("inventario-fisico", reverse("stock:inventario"))
