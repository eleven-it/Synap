# -*- coding: utf-8 -*-
"""Tests ajuste post-snapshot inventario físico (funciones puras y recalc)."""
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from stock.services import inventario_fisico as svc


class FuncionesPurasAjustePostSnapshotTest(SimpleTestCase):
    def test_ajuste_efectivo_usa_manual_si_existe(self):
        self.assertEqual(
            svc.ajuste_efectivo(Decimal("5"), Decimal("-2")),
            Decimal("-2"),
        )

    def test_ajuste_efectivo_sistema_si_manual_none(self):
        self.assertEqual(
            svc.ajuste_efectivo(Decimal("3.5"), None),
            Decimal("3.5"),
        )

    def test_ajuste_efectivo_cero_si_ambos_none(self):
        self.assertEqual(svc.ajuste_efectivo(None, None), Decimal("0"))

    def test_calcular_disponible_ajustado(self):
        self.assertEqual(
            svc.calcular_disponible_ajustado(Decimal("100"), Decimal("7")),
            Decimal("107"),
        )

    def test_calcular_diferencia_real_contado_menos_disponible(self):
        self.assertEqual(
            svc.calcular_diferencia_real(Decimal("12"), Decimal("10")),
            Decimal("2"),
        )

    def test_calcular_diferencia_real_none_si_no_contado(self):
        self.assertIsNone(svc.calcular_diferencia_real(None, Decimal("10")))

    def test_hay_descuadre_true_si_saldo_ref_difiere(self):
        self.assertTrue(
            svc.hay_descuadre(
                saldo_snapshot=Decimal("10"),
                ajuste_sistema=Decimal("3"),
                saldo_actual_ref=Decimal("14"),
            )
        )

    def test_hay_descuadre_false_si_coincide(self):
        self.assertFalse(
            svc.hay_descuadre(
                saldo_snapshot=Decimal("10"),
                ajuste_sistema=Decimal("3"),
                saldo_actual_ref=Decimal("13"),
            )
        )

    def test_hay_descuadre_false_si_ref_none(self):
        self.assertFalse(
            svc.hay_descuadre(
                saldo_snapshot=Decimal("10"),
                ajuste_sistema=Decimal("3"),
                saldo_actual_ref=None,
            )
        )

    def test_hay_descuadre_false_si_coincide_con_mov_post(self):
        self.assertFalse(
            svc.hay_descuadre(
                saldo_snapshot=Decimal("640"),
                ajuste_sistema=Decimal("1293"),
                saldo_actual_ref=Decimal("2860"),
                mov_post_conteo=Decimal("927"),
            )
        )
    def test_saldo_final_actual_mas_diferencia(self):
        self.assertEqual(
            svc.calcular_saldo_final_post_mstock(
                Decimal("11347"),
                Decimal("5879"),
                Decimal("5558"),
                disponible_ajustado=Decimal("5468"),
            ),
            Decimal("11437"),
        )

    def test_saldo_final_sin_descuadre_coincide_con_contado(self):
        self.assertEqual(
            svc.calcular_saldo_final_post_mstock(
                Decimal("11347"),
                Decimal("5879"),
                Decimal("5468"),
                disponible_ajustado=Decimal("5468"),
            ),
            Decimal("11347"),
        )

    def test_saldo_final_none_si_no_contado(self):
        self.assertIsNone(
            svc.calcular_saldo_final_post_mstock(
                None,
                None,
                Decimal("100"),
                disponible_ajustado=Decimal("100"),
            )
        )

    def test_enriquecer_linea_incluye_saldo_final(self):
        linea = svc.enriquecer_linea_analizador(
            {
                "saldo_snapshot": Decimal("4853"),
                "ajuste_sistema": Decimal("615"),
                "ajuste_manual": None,
                "cantidad_contada": Decimal("11347"),
                "saldo_actual_ref": Decimal("5558"),
            }
        )
        self.assertEqual(linea["disponible_ajustado"], Decimal("5468"))
        self.assertEqual(linea["diferencia_real"], Decimal("5879"))
        self.assertEqual(linea["saldo_final"], Decimal("11437"))
        self.assertTrue(linea["descuadre"])
        self.assertEqual(
            linea["formula_diferencia"],
            "11347 − (4853 + 615) = 5879",
        )


class ResolverTsConteoLineaTest(SimpleTestCase):
    def test_match_cantidad_mas_reciente(self):
        eventos = [
            {
                "id_evento": 1,
                "cantidad": Decimal("5"),
                "server_ts": datetime(2026, 8, 10, 9, 0, 0),
                "resultado": svc.RESULTADO_ACEPTADO,
            },
            {
                "id_evento": 2,
                "cantidad": Decimal("12"),
                "server_ts": datetime(2026, 8, 10, 11, 0, 0),
                "resultado": svc.RESULTADO_ACEPTADO,
            },
        ]
        ts = svc.resolver_ts_conteo_linea(eventos, Decimal("12"))
        self.assertEqual(ts, datetime(2026, 8, 10, 11, 0, 0))

    def test_sin_match_usa_ultimo_aceptado(self):
        eventos = [
            {
                "id_evento": 1,
                "cantidad": Decimal("5"),
                "client_ts": "2026-08-10 09:00:00",
                "resultado": svc.RESULTADO_ACEPTADO,
            },
            {
                "id_evento": 2,
                "cantidad": Decimal("7"),
                "client_ts": "2026-08-10 10:00:00",
                "resultado": svc.RESULTADO_CONFLICTO,
            },
        ]
        ts = svc.resolver_ts_conteo_linea(eventos, Decimal("99"))
        self.assertEqual(ts, datetime(2026, 8, 10, 9, 0, 0))

    def test_prefer_server_ts_sobre_client_ts(self):
        eventos = [
            {
                "id_evento": 1,
                "cantidad": Decimal("3"),
                "server_ts": datetime(2026, 8, 10, 12, 0, 0),
                "client_ts": "2026-08-10 08:00:00",
                "resultado": svc.RESULTADO_ACEPTADO,
            }
        ]
        ts = svc.resolver_ts_conteo_linea(eventos, Decimal("3"))
        self.assertEqual(ts, datetime(2026, 8, 10, 12, 0, 0))

    def test_none_sin_eventos(self):
        self.assertIsNone(svc.resolver_ts_conteo_linea([], Decimal("1")))


class CalcularNetoMovimientosPostSnapshotTest(SimpleTestCase):
    def _movs(self):
        return [
            {
                "FechaControl": datetime(2026, 8, 5, 10, 0, 0),
                "Entrada": Decimal("10"),
                "Salida": Decimal("0"),
            },
            {
                "FechaControl": datetime(2026, 8, 6, 10, 0, 0),
                "Entrada": Decimal("0"),
                "Salida": Decimal("3"),
            },
            {
                "FechaControl": datetime(2026, 8, 8, 10, 0, 0),
                "Entrada": Decimal("0"),
                "Salida": Decimal("2"),
            },
        ]

    def test_neto_hasta_conteo_excluye_movs_posteriores(self):
        neto = svc.calcular_neto_movimientos_post_snapshot(
            self._movs(),
            fecha_hasta=datetime(2026, 8, 6, 23, 59, 59),
        )
        self.assertEqual(neto, Decimal("7"))

    def test_neto_sin_tope_suma_todos(self):
        neto = svc.calcular_neto_movimientos_post_snapshot(self._movs())
        self.assertEqual(neto, Decimal("5"))


class CalcularAjusteSistemaLineaTest(SimpleTestCase):
    def test_contado_usa_movs_hasta_t_conteo(self):
        t_conteo = datetime(2026, 8, 6, 12, 0, 0)
        movs = [
            {
                "FechaControl": datetime(2026, 8, 5, 10, 0, 0),
                "Entrada": Decimal("4"),
                "Salida": Decimal("0"),
            },
            {
                "FechaControl": datetime(2026, 8, 7, 10, 0, 0),
                "Entrada": Decimal("0"),
                "Salida": Decimal("9"),
            },
        ]
        eventos = [
            {
                "id_evento": 1,
                "cantidad": Decimal("20"),
                "server_ts": t_conteo,
                "resultado": svc.RESULTADO_ACEPTADO,
            }
        ]
        ajuste, fallback = svc.calcular_ajuste_sistema_linea(Decimal("20"), movs, eventos)
        self.assertEqual(ajuste, Decimal("4"))
        self.assertFalse(fallback)

    def test_sin_conteo_neto_hasta_ahora(self):
        movs = [
            {
                "FechaControl": datetime(2026, 8, 7, 10, 0, 0),
                "Entrada": Decimal("2"),
                "Salida": Decimal("0"),
            }
        ]
        ajuste, fallback = svc.calcular_ajuste_sistema_linea(None, movs, [])
        self.assertEqual(ajuste, Decimal("2"))
        self.assertFalse(fallback)


class ClasificarMovimientoPostSnapshotTest(SimpleTestCase):
    def test_remitos_facturas_nc(self):
        self.assertEqual(svc.clasificar_movimiento_post_snapshot("REM"), svc.CAT_REMITOS)
        self.assertEqual(svc.clasificar_movimiento_post_snapshot("FA"), svc.CAT_FACTURAS)
        self.assertEqual(svc.clasificar_movimiento_post_snapshot("NCA"), svc.CAT_NOTAS_CREDITO)

    def test_mstock_armado_vs_ajuste(self):
        self.assertEqual(
            svc.clasificar_movimiento_post_snapshot("MSTOCK", "Movimiento", "Armado 1ra OPT"),
            svc.CAT_ARMADO_MPR,
        )
        self.assertEqual(
            svc.clasificar_movimiento_post_snapshot("MSTOCK", "Faltante", "Ajuste conteo"),
            svc.CAT_AJUSTES,
        )

    def test_chips_y_suma_categorias(self):
        desglose = {
            **svc.desglose_post_snapshot_vacio(),
            "armado_mpr": Decimal("100"),
            "remitos": Decimal("-40"),
            "total": Decimal("60"),
        }
        chips = svc.chips_desglose_post_snapshot(desglose)
        self.assertEqual(len(chips), 2)
        self.assertEqual(chips[0]["etiqueta"], "Entradas armado MPR")
        self.assertEqual(
            sum((c["neto"] for c in chips), Decimal("0")),
            Decimal("60"),
        )


class RecalcularAjustePostSnapshotTest(SimpleTestCase):
    def _campana_en_revision(self):
        return {
            "id_campana": 7,
            "estado": svc.ESTADO_EN_REVISION,
            "fecha_snapshot": "2026-08-04 08:00:00",
            "depositos": [3],
        }

    @patch("stock.services.inventario_fisico._cargar_movimientos_post_snapshot_campana")
    @patch("stock.services.inventario_fisico._cargar_eventos_campana")
    @patch("stock.services.inventario_fisico._fetch_saldos_deposito")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_recalc_preserva_override_sin_pisar(
        self, mock_cursor_ctx, mock_obtener, mock_saldos, mock_eventos, mock_movs
    ):
        mock_obtener.return_value = self._campana_en_revision()
        t_conteo = datetime(2026, 8, 10, 12, 0, 0)
        mock_eventos.return_value = {
            (100, 3): [
                {
                    "id_evento": 1,
                    "cantidad": Decimal("20"),
                    "server_ts": t_conteo,
                    "resultado": svc.RESULTADO_ACEPTADO,
                }
            ]
        }
        mock_movs.return_value = {
            (100, 3): [
                {
                    "FechaControl": datetime(2026, 8, 5, 10, 0, 0),
                    "Entrada": Decimal("5"),
                    "Salida": Decimal("0"),
                },
                {
                    "FechaControl": datetime(2026, 8, 11, 10, 0, 0),
                    "Entrada": Decimal("0"),
                    "Salida": Decimal("99"),
                },
            ]
        }
        mock_saldos.return_value = {3: Decimal("23")}

        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        lineas_db = [
            {
                "id_linea": 1,
                "id_articulo": 100,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("20"),
                "ajuste_manual": Decimal("8"),
            }
        ]
        cursor.fetchall.side_effect = [lineas_db]

        ok, result = svc.recalcular_ajuste_post_snapshot(
            "emp", 7, id_usuario=1, pisar_overrides=False
        )

        self.assertTrue(ok, result)
        self.assertEqual(result["lineas_actualizadas"], 1)
        self.assertEqual(result["overrides_pisados"], 0)

        update_sql = cursor.execute.call_args_list[-1].args[0]
        self.assertIn("ajuste_calculado_at = NOW()", update_sql)
        self.assertNotIn("ajuste_manual = NULL", update_sql)

        params = cursor.execute.call_args_list[-1].args[1]
        ajuste_sys, saldo_ref, diff_real, _id_linea = params
        self.assertEqual(ajuste_sys, Decimal("5"))
        self.assertEqual(saldo_ref, Decimal("23"))
        # contado 20 - (snapshot 10 + override 8) = 2
        self.assertEqual(diff_real, Decimal("2"))

    @patch("stock.services.inventario_fisico._insert_auditoria_ajuste")
    @patch("stock.services.inventario_fisico._cargar_movimientos_post_snapshot_campana")
    @patch("stock.services.inventario_fisico._cargar_eventos_campana")
    @patch("stock.services.inventario_fisico._fetch_saldos_deposito")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_recalc_pisa_override_con_flag(
        self, mock_cursor_ctx, mock_obtener, mock_saldos, mock_eventos, mock_movs, mock_auditoria
    ):
        mock_obtener.return_value = self._campana_en_revision()
        t_conteo = datetime(2026, 8, 10, 12, 0, 0)
        mock_eventos.return_value = {
            (100, 3): [
                {
                    "id_evento": 1,
                    "cantidad": Decimal("20"),
                    "server_ts": t_conteo,
                    "resultado": svc.RESULTADO_ACEPTADO,
                }
            ]
        }
        mock_movs.return_value = {
            (100, 3): [
                {
                    "FechaControl": datetime(2026, 8, 5, 10, 0, 0),
                    "Entrada": Decimal("5"),
                    "Salida": Decimal("0"),
                }
            ]
        }
        mock_saldos.return_value = {3: Decimal("15")}

        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        lineas_db = [
            {
                "id_linea": 1,
                "id_articulo": 100,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("10"),
                "cantidad_contada": Decimal("20"),
                "ajuste_manual": Decimal("8"),
            }
        ]
        cursor.fetchall.side_effect = [lineas_db]

        ok, result = svc.recalcular_ajuste_post_snapshot(
            "emp", 7, id_usuario=9, pisar_overrides=True
        )

        self.assertTrue(ok, result)
        self.assertEqual(result["overrides_pisados"], 1)
        mock_auditoria.assert_called_once()

        update_sql = cursor.execute.call_args_list[-1].args[0]
        self.assertIn("ajuste_manual = NULL", update_sql)

        params = cursor.execute.call_args_list[-1].args[1]
        _ajuste_sys, _saldo_ref, diff_real, _id_linea = params
        # contado 20 - (snapshot 10 + sistema 5) = 5
        self.assertEqual(diff_real, Decimal("5"))

    @patch("stock.services.inventario_fisico._cargar_movimientos_post_snapshot_campana")
    @patch("stock.services.inventario_fisico._cargar_eventos_campana")
    @patch("stock.services.inventario_fisico._fetch_saldos_deposito")
    @patch("stock.services.inventario_fisico.obtener_campana")
    @patch("stock.services.inventario_fisico.mysql_cursor")
    def test_recalc_diff_en_momento_conteo_excluye_movs_b(
        self, mock_cursor_ctx, mock_obtener, mock_saldos, mock_eventos, mock_movs
    ):
        mock_obtener.return_value = self._campana_en_revision()
        t_conteo = datetime(2026, 8, 6, 15, 0, 0)
        mock_eventos.return_value = {
            (100, 3): [
                {
                    "id_evento": 1,
                    "cantidad": Decimal("25"),
                    "server_ts": t_conteo,
                    "resultado": svc.RESULTADO_ACEPTADO,
                }
            ]
        }
        mock_movs.return_value = {
            (100, 3): [
                {
                    "FechaControl": datetime(2026, 8, 5, 10, 0, 0),
                    "Entrada": Decimal("3"),
                    "Salida": Decimal("0"),
                },
                {
                    "FechaControl": datetime(2026, 8, 7, 10, 0, 0),
                    "Entrada": Decimal("0"),
                    "Salida": Decimal("50"),
                },
            ]
        }
        mock_saldos.return_value = {3: Decimal("100")}

        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        lineas_db = [
            {
                "id_linea": 1,
                "id_articulo": 100,
                "id_deposito": 3,
                "saldo_snapshot": Decimal("20"),
                "cantidad_contada": Decimal("25"),
                "ajuste_manual": None,
            }
        ]
        cursor.fetchall.side_effect = [lineas_db]

        ok, result = svc.recalcular_ajuste_post_snapshot(
            "emp", 7, id_usuario=1, pisar_overrides=False
        )

        self.assertTrue(ok, result)
        params = cursor.execute.call_args_list[-1].args[1]
        ajuste_sys, saldo_ref, diff_real, _id_linea = params
        self.assertEqual(ajuste_sys, Decimal("3"))
        self.assertEqual(saldo_ref, Decimal("100"))
        self.assertEqual(diff_real, Decimal("2"))

    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_recalc_omitido_estado_final(self, mock_obtener):
        mock_obtener.return_value = {
            "id_campana": 7,
            "estado": svc.ESTADO_APLICADO,
        }
        ok, result = svc.recalcular_ajuste_post_snapshot(
            "emp", 7, id_usuario=1, pisar_overrides=False
        )
        self.assertTrue(ok)
        self.assertTrue(result.get("omitido"))


class FaseMovimientoConteoTest(SimpleTestCase):
    def test_es_mstock_cierre_inventario(self):
        self.assertTrue(
            svc.es_mstock_cierre_inventario(
                "MSTOCK",
                "Inventario físico campaña #10 cierre",
                10,
            )
        )
        self.assertFalse(
            svc.es_mstock_cierre_inventario(
                "MSTOCK",
                "Armado 1ra OPT",
                10,
            )
        )
        self.assertFalse(
            svc.es_mstock_cierre_inventario("REM", "Inventario físico campaña #10", 10)
        )

    def test_clasificar_fase_hasta_y_post(self):
        t_conteo = datetime(2026, 9, 9, 13, 52, 0)
        self.assertEqual(
            svc.clasificar_fase_movimiento_conteo(
                datetime(2026, 9, 8, 10, 0, 0),
                t_conteo,
                "REM",
                "",
                10,
            ),
            svc.FASE_HASTA_CONTEO,
        )
        self.assertEqual(
            svc.clasificar_fase_movimiento_conteo(
                datetime(2026, 9, 10, 10, 0, 0),
                t_conteo,
                "REM",
                "",
                10,
            ),
            svc.FASE_POST_CONTEO,
        )
        self.assertEqual(
            svc.clasificar_fase_movimiento_conteo(
                datetime(2026, 9, 15, 10, 0, 0),
                t_conteo,
                "MSTOCK",
                "Inventario físico campaña #10",
                10,
            ),
            svc.FASE_MSTOCK_CIERRE,
        )


class ResumenEscenarioLineaTest(SimpleTestCase):
    def test_contada_sin_mov_antes(self):
        esc = svc.resumen_escenario_linea(Decimal("100"), Decimal("0"), Decimal("0"))
        self.assertEqual(esc["escenario_antes"], "sin_mov_antes_conteo")
        self.assertEqual(esc["escenario_despues"], "sin_mov_post_conteo")

    def test_contada_con_mov_antes(self):
        esc = svc.resumen_escenario_linea(Decimal("100"), Decimal("6"), Decimal("0"))
        self.assertEqual(esc["escenario_antes"], "con_mov_antes_conteo")

    def test_contada_con_mov_despues(self):
        esc = svc.resumen_escenario_linea(Decimal("100"), Decimal("0"), Decimal("6"))
        self.assertEqual(esc["escenario_despues"], "con_mov_post_conteo")
        self.assertIn("+6", esc["escenario_despues_etiqueta"])

    def test_sin_conteo(self):
        esc = svc.resumen_escenario_linea(None, Decimal("3"), Decimal("5"))
        self.assertEqual(esc["escenario_antes"], "sin_conteo")
        self.assertEqual(esc["escenario_despues"], "sin_conteo")


class ParticionarMovimientosTest(SimpleTestCase):
    def test_separa_a_b_y_mstock(self):
        t_conteo = datetime(2026, 9, 9, 13, 52, 0)
        movs = [
            {
                "FechaControl": datetime(2026, 9, 8, 10, 0, 0),
                "Entrada": Decimal("0"),
                "Salida": Decimal("0"),
                "Comprobante": "REM",
                "detalle": "",
            },
            {
                "FechaControl": datetime(2026, 9, 10, 10, 0, 0),
                "Entrada": Decimal("6"),
                "Salida": Decimal("0"),
                "Comprobante": "REM",
                "detalle": "",
            },
            {
                "FechaControl": datetime(2026, 9, 15, 10, 0, 0),
                "Entrada": Decimal("2600"),
                "Salida": Decimal("0"),
                "Comprobante": "MSTOCK",
                "detalle": "Inventario físico campaña #10",
            },
        ]
        hasta, post, post_omit, mstock_omit = svc._particionar_movimientos_por_fase(
            movs,
            t_conteo=t_conteo,
            id_campana=10,
            cantidad_contada=Decimal("1747"),
        )
        self.assertEqual(len(hasta), 1)
        self.assertEqual(len(post), 1)
        self.assertEqual(post_omit, 1)
        self.assertEqual(mstock_omit, 1)
        self.assertEqual(
            svc.calcular_neto_movimientos_post_snapshot(post),
            Decimal("6"),
        )


class ListarMovimientosPostSnapshotFiltroTest(SimpleTestCase):
    @patch("stock.services.inventario_fisico.mysql_cursor")
    @patch("stock.services.inventario_fisico.listar_eventos_linea")
    @patch("stock.services.inventario_fisico.obtener_campana")
    def test_solo_hasta_conteo_excluye_post_y_mstock(
        self, mock_campana, mock_eventos, mock_cursor_ctx
    ):
        mock_campana.return_value = {
            "fecha_snapshot": datetime(2026, 9, 1, 8, 0, 0),
        }
        t_conteo = datetime(2026, 9, 9, 13, 52, 0)
        mock_eventos.return_value = [
            {
                "id_evento": 1,
                "cantidad": Decimal("1747"),
                "server_ts": t_conteo,
                "resultado": svc.RESULTADO_ACEPTADO,
            }
        ]
        cursor = MagicMock()
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [
            {
                "id_stock": 1,
                "FechaControl": datetime(2026, 9, 8, 10, 0, 0),
                "Fecha": None,
                "Entrada": Decimal("0"),
                "Salida": Decimal("0"),
                "comprobante": "REM",
                "motivo": "-",
                "nro": "1",
                "detalle": "",
            },
            {
                "id_stock": 2,
                "FechaControl": datetime(2026, 9, 10, 10, 0, 0),
                "Fecha": None,
                "Entrada": Decimal("6"),
                "Salida": Decimal("0"),
                "comprobante": "REM",
                "motivo": "-",
                "nro": "2",
                "detalle": "",
            },
            {
                "id_stock": 3,
                "FechaControl": datetime(2026, 9, 15, 10, 0, 0),
                "Fecha": None,
                "Entrada": Decimal("2600"),
                "Salida": Decimal("0"),
                "comprobante": "MSTOCK",
                "motivo": "-",
                "nro": "3",
                "detalle": "Inventario físico campaña #10",
            },
        ]
        cursor.execute = MagicMock(side_effect=lambda *a, **k: None)
        cursor._nombre_tabla = MagicMock(return_value="stock")

        with patch(
            "stock.services.inventario_fisico._nombre_tabla",
            side_effect=lambda c, t: "stock" if t == "stock" else None,
        ):
            movs = svc.listar_movimientos_post_snapshot(
                "emp",
                10,
                14,
                3,
                cantidad_contada=Decimal("1747"),
                solo_hasta_conteo=True,
            )

        self.assertEqual(len(movs), 1)
        self.assertEqual(movs[0]["fase"], svc.FASE_HASTA_CONTEO)
