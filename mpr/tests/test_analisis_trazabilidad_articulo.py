"""Tests TDD servicio análisis trazabilidad artículo (PR1 collector + fórmulas)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import listar_demanda_ped_por_articulo
from mpr.services_kardex_articulo import (
    _afecta_deposito_terminado,
    _calcular_saldo_corrido_analisis,
    _calcular_saldo_inicial_terminado,
    _clasificar_movimiento_analisis,
    _deduplicar_movimientos,
    _unificar_y_saldo_corrido,
    construir_analisis_trazabilidad_articulo,
)


class TestAfectaDepositoTerminado(SimpleTestCase):
    def test_rem_afecta_deposito(self):
        self.assertTrue(_afecta_deposito_terminado("REM"))

    def test_fa_no_afecta_deposito(self):
        self.assertFalse(_afecta_deposito_terminado("FA"))


class TestClasificarMovimientoAnalisis(SimpleTestCase):
    def test_opa_clase_ui(self):
        clase, afecta = _clasificar_movimiento_analisis(
            tipo_mov="OPA",
            motivo_movimiento="Armado",
            comprobante="MSTOCK",
        )
        self.assertEqual(clase, "opa")
        self.assertTrue(afecta)

    def test_opp_clase_ui(self):
        clase, _ = _clasificar_movimiento_analisis(
            tipo_mov="OPP",
            motivo_movimiento="",
            comprobante="MSTOCK",
        )
        self.assertEqual(clase, "opp")

    def test_rem_clase_ui(self):
        clase, afecta = _clasificar_movimiento_analisis(
            tipo_mov="REM",
            motivo_movimiento="",
            comprobante="REM",
        )
        self.assertEqual(clase, "rem")
        self.assertTrue(afecta)

    def test_fa_clase_ui_sin_efecto_deposito(self):
        clase, afecta = _clasificar_movimiento_analisis(
            tipo_mov="FA",
            motivo_movimiento="",
            comprobante="FA",
        )
        self.assertEqual(clase, "fa")
        self.assertFalse(afecta)

    def test_inventario_por_motivo(self):
        clase, afecta = _clasificar_movimiento_analisis(
            tipo_mov="",
            motivo_movimiento="Inventario físico faltante campaña",
            comprobante="MSTOCK",
            tipo_comp="Faltante",
        )
        self.assertEqual(clase, "inventario")
        self.assertTrue(afecta)

    def test_inventario_por_motivo_conteo(self):
        clase, afecta = _clasificar_movimiento_analisis(
            tipo_mov="",
            motivo_movimiento="Ajuste por conteo físico",
            comprobante="MSTOCK",
            tipo_comp="Conteo",
        )
        self.assertEqual(clase, "inventario")
        self.assertTrue(afecta)

    def test_stock_inicial_por_tipo_comp(self):
        clase, afecta = _clasificar_movimiento_analisis(
            tipo_mov="",
            motivo_movimiento="",
            comprobante="MSTOCK",
            tipo_comp="Stock Inicial",
        )
        self.assertEqual(clase, "stock_inicial")
        self.assertTrue(afecta)


class TestConsultarInventarioMstockParams(SimpleTestCase):
    """Regresión: orden de binds IDArt + LIKE (faltante/sobrante/inventario/conteo/stock inicial)."""

    @patch("mpr.services_kardex_articulo.mysql_cursor")
    @patch("mpr.services._nombre_tabla", side_effect=lambda _c, t: t)
    def test_params_id_art_antes_de_likes(self, _nt, mock_cursor_ctx):
        from mpr.services_kardex_articulo import _consultar_movimientos_inventario_mstock

        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _cm(*_a, **_k):
            yield cursor

        mock_cursor_ctx.side_effect = _cm
        _consultar_movimientos_inventario_mstock(
            "empresa92",
            1399,
            fecha_desde="2026-07-01",
            fecha_hasta="2026-09-30",
            limit=100,
        )
        args = cursor.execute.call_args[0]
        params = list(args[1])
        self.assertEqual(params[0], 1399)
        self.assertEqual(params[1], "%faltante%")
        self.assertEqual(params[2], "%sobrante%")
        self.assertEqual(params[3], "%inventario%")
        self.assertEqual(params[4], "%conteo%")
        self.assertEqual(params[5], "%stock inicial%")
        self.assertEqual(params[6], "2026-07-01")
        self.assertEqual(params[7], "2026-09-30 23:59:59")
        self.assertEqual(params[8], 100)


class TestDeduplicarMovimientos(SimpleTestCase):
    def test_prefiere_mstock_sobre_mpr_parte(self):
        movs = [
            {
                "codigo_movimiento": 500,
                "clase_ui": "opp",
                "fuente": "mpr_parte",
                "entrada": 10,
                "salida": 0,
            },
            {
                "codigo_movimiento": 500,
                "clase_ui": "opp",
                "fuente": "mstock",
                "entrada": 10,
                "salida": 0,
            },
        ]
        out = _deduplicar_movimientos(movs)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["fuente"], "mstock")

    def test_mantiene_codigos_distintos(self):
        movs = [
            {"codigo_movimiento": 1, "fuente": "mstock", "entrada": 5, "salida": 0},
            {"codigo_movimiento": 2, "fuente": "mstock", "entrada": 3, "salida": 0},
        ]
        out = _deduplicar_movimientos(movs)
        self.assertEqual(len(out), 2)


class TestConsultarEventosMprSinDuplicarOpa(SimpleTestCase):
    @patch("mpr.services.reporte_mpr_trazabilidad_componente")
    def test_omite_opa_opp_mstock_del_helper_timeline(self, mock_rep):
        """El collector MPR solo pasa envío/parte/clasificación (OPA ya viene de kardex)."""
        from mpr.services_kardex_articulo import _consultar_eventos_mpr_articulo

        mock_rep.return_value = {
            "eventos": [
                {"tipo": "envio", "cantidad": 10, "fecha_sort": "2026-08-01"},
                {"tipo": "opa", "cantidad": 42, "fecha_sort": "2026-08-03"},
                {"tipo": "opp", "cantidad": 5, "fecha_sort": "2026-08-02"},
                {"tipo": "parte", "cantidad": 8, "fecha_sort": "2026-08-02"},
                {"tipo": "clasificacion", "cantidad": 3, "fecha_sort": "2026-08-04"},
            ]
        }
        out = _consultar_eventos_mpr_articulo("emp", 1, fecha_desde="2026-07-01", fecha_hasta="2026-09-01")
        tipos = [e["tipo"] for e in out]
        self.assertEqual(tipos, ["envio", "parte", "clasificacion"])
        self.assertTrue(all(e["clase_ui"].startswith("mpr_") for e in out))


class TestSaldoCorridoAnalisis(SimpleTestCase):
    def test_fa_no_mueve_saldo_corrido(self):
        movs = [
            {
                "entrada": 0,
                "salida": 15,
                "afecta_deposito": False,
                "clase_ui": "fa",
            },
            {
                "entrada": 10,
                "salida": 0,
                "afecta_deposito": True,
                "clase_ui": "opa",
            },
        ]
        out = _calcular_saldo_corrido_analisis(movs, saldo_inicial=50)
        self.assertEqual(out[0]["saldo_corrido"], 50)
        self.assertEqual(out[1]["saldo_corrido"], 60)

    def test_unificar_y_saldo_corrido_orden_cronologico(self):
        movs = [
            {
                "fecha_sort": date(2026, 8, 2),
                "codigo_movimiento": 2,
                "entrada": 0,
                "salida": 30,
                "afecta_deposito": True,
                "clase_ui": "opa",
            },
            {
                "fecha_sort": date(2026, 8, 1),
                "codigo_movimiento": 1,
                "entrada": 100,
                "salida": 0,
                "afecta_deposito": True,
                "clase_ui": "opp",
            },
        ]
        out = _unificar_y_saldo_corrido(movs, saldo_inicial=50)
        self.assertEqual(out[0]["codigo_movimiento"], 1)
        self.assertEqual(out[0]["saldo_corrido"], 150)
        self.assertEqual(out[1]["saldo_corrido"], 120)

    def test_inventario_expone_conteo_igual_saldo_corrido(self):
        movs = [
            {
                "entrada": 0,
                "salida": 167,
                "afecta_deposito": True,
                "clase_ui": "rem",
            },
            {
                "entrada": 167,
                "salida": 0,
                "afecta_deposito": True,
                "clase_ui": "inventario",
            },
        ]
        out = _calcular_saldo_corrido_analisis(movs, saldo_inicial=167)
        self.assertIsNone(out[0]["conteo"])
        self.assertEqual(out[1]["conteo"], 167)
        self.assertEqual(out[1]["saldo_corrido"], 167)


class TestCalcularSaldoInicialTerminado(SimpleTestCase):
    def test_saldo_inicial_desde_movimientos_previos(self):
        pre_periodo = [
            {"entrada": 40, "salida": 0, "afecta_deposito": True},
            {"entrada": 0, "salida": 10, "afecta_deposito": True},
        ]
        saldo, ok = _calcular_saldo_inicial_terminado(pre_periodo_movimientos=pre_periodo)
        self.assertTrue(ok)
        self.assertEqual(saldo, 30)

    def test_fa_previo_no_suma_saldo_inicial(self):
        pre_periodo = [
            {"entrada": 0, "salida": 20, "afecta_deposito": False, "clase_ui": "fa"},
            {"entrada": 50, "salida": 0, "afecta_deposito": True, "clase_ui": "opp"},
        ]
        saldo, ok = _calcular_saldo_inicial_terminado(pre_periodo_movimientos=pre_periodo)
        self.assertTrue(ok)
        self.assertEqual(saldo, 50)


class TestListarDemandaPedPorArticulo(SimpleTestCase):
    @patch("mpr.services._listar_demanda_ped_vivo_fifo")
    def test_delega_en_fifo_vivo(self, mock_fifo):
        mock_fifo.return_value = [
            {
                "codigo_movimiento_pedido": 9001,
                "cantidad_pendiente_prod": 25,
                "nro_pedido": "PED-001",
            }
        ]
        out = listar_demanda_ped_por_articulo("empresa92", 1398, limit=10)
        mock_fifo.assert_called_once_with("empresa92", 1398, limit=10)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["cantidad_pendiente_prod"], 25)


class TestConstruirAnalisisTrazabilidadArticulo(SimpleTestCase):
    """Integración payload design + fórmulas brecha pack 610."""

    PACK_610_ID = 1398

    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Terminado")
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._consultar_movimientos_inventario_mstock", return_value=[])
    @patch("mpr.services_kardex_articulo._consultar_movimientos_stock_rem_fa", return_value=[])
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=0)
    @patch("mpr.services.get_bom_detalle", return_value=None)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=24)
    @patch("mpr.services.listar_demanda_ped_por_articulo")
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis")
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo")
    @patch("mpr.services_kardex_articulo._consultar_movimientos_kardex_articulo")
    @patch("mpr.services._fetch_descripciones_articulo")
    def test_payload_bloques_y_formulas_brecha(
        self,
        mock_desc,
        mock_mstock,
        mock_reserva,
        mock_stock,
        mock_demanda,
        *_mocks,
    ):
        mock_desc.return_value = {
            self.PACK_610_ID: ("610", "610 T6 Kamp Tripack Bl/Gm/Ne 3P"),
        }
        mock_demanda.return_value = [
            {
                "codigo_movimiento_pedido": 8001,
                "cantidad_pendiente_prod": 100,
                "nro_pedido": "0001-00012345",
                "nombre_cliente": "Cliente Test",
                "fecha": "01/07/2026",
            }
        ]
        mock_stock.return_value = -20
        mock_reserva.return_value = 30
        mock_mstock.return_value = [
            {
                "codigo_movimiento": 100,
                "fecha": date(2026, 8, 1),
                "tipo_mov": "OPP",
                "motivo_movimiento": "Parte producción",
                "nro_comprobante": "0001-00000100",
                "detalle": "Entrada",
                "id_operario_opt": 5,
                "total_entrada": 10,
                "total_salida": 0,
            },
        ]

        payload = construir_analisis_trazabilidad_articulo(
            "empresa92",
            self.PACK_610_ID,
            fecha_desde="2026-07-01",
            fecha_hasta="2026-09-30",
        )

        self.assertEqual(payload["articulo"]["id"], self.PACK_610_ID)
        self.assertEqual(payload["deposito"]["id"], 6)
        self.assertTrue(payload["deposito"]["es_default_canonico"])
        self.assertIn("demanda_ped", payload)
        self.assertIn("stock", payload)
        self.assertIn("brechas", payload)
        self.assertIn("movimientos", payload)
        self.assertIn("kpis", payload)
        self.assertIn("saldo_inicial", payload)
        self.assertEqual(payload["demanda_ped"]["totales"]["p_ped"], 100)
        self.assertEqual(payload["demanda_ped"]["totales"]["stock"], -20)
        self.assertEqual(payload["demanda_ped"]["totales"]["cubierto_stock"], 0)
        self.assertEqual(payload["demanda_ped"]["totales"]["ped_urgente"], 120)
        self.assertEqual(payload["stock"]["terminado"], -20)
        self.assertTrue(payload["stock"]["negativo"])
        self.assertEqual(payload["brechas"]["ped_urgente"], 120)
        self.assertEqual(payload["brechas"]["tot_urgente"], 150)
        self.assertIn("Terminado", payload["brechas"]["texto_explicativo"])
        self.assertEqual(payload["kpis"]["pedido"], 100)
        self.assertEqual(payload["kpis"]["ped_urgente"], 120)
        self.assertEqual(payload["kpis"]["tot_urgente"], 150)
        self.assertTrue(payload["a_producir"]["alerta_semi_cero"])

    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Terminado")
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._consultar_movimientos_inventario_mstock", return_value=[])
    @patch(
        "mpr.services_kardex_articulo._consultar_movimientos_stock_rem_fa",
        return_value=[
            {
                "codigo_movimiento": 200,
                "fecha": date(2026, 8, 5),
                "comprobante": "FA",
                "tipo_mov": "FA",
                "nro_comprobante": "0001-FA-001",
                "detalle": "Factura",
                "total_entrada": 0,
                "total_salida": 5,
            }
        ],
    )
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=10)
    @patch("mpr.services.get_bom_detalle", return_value=None)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=50)
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch("mpr.services_kardex_articulo._consultar_movimientos_kardex_articulo", return_value=[])
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={615: ("907944-02", "Pack prueba")},
    )
    def test_fa_omitida_porque_no_mueve_stock(self, *_mocks):
        payload = construir_analisis_trazabilidad_articulo(
            "empresa92",
            615,
            fecha_desde="2026-08-01",
            fecha_hasta="2026-08-31",
        )
        fa_rows = [m for m in payload["movimientos"] if m.get("clase_ui") == "fa"]
        self.assertEqual(len(fa_rows), 0)
        self.assertEqual(payload["movimientos"], [])

    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Semi elaborado")
    @patch("mpr.services.get_deposito_semi_elaborado_mpr", return_value=3)
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=0)
    @patch("mpr.services.get_bom_detalle", return_value=None)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=80)
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch("mpr.services._fetch_descripciones_articulo", return_value={615: ("X", "Art")})
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis")
    def test_pre_periodo_solo_alimenta_saldo_inicial(self, mock_recolectar, *_mocks):
        """Movimientos anteriores al Desde no se listan; suben el saldo inicial."""

        def _side_effect(*args, **kwargs):
            if kwargs.get("solo_pre_periodo"):
                return [
                    {
                        "fecha_sort": date(2026, 6, 1),
                        "codigo_movimiento": 1,
                        "entrada": 100,
                        "salida": 0,
                        "afecta_deposito": True,
                        "clase_ui": "opp",
                        "nro_comprobante": "PRE-1",
                    }
                ]
            return [
                {
                    "fecha_sort": date(2026, 8, 10),
                    "codigo_movimiento": 2,
                    "entrada": 0,
                    "salida": 20,
                    "afecta_deposito": True,
                    "clase_ui": "rem",
                    "nro_comprobante": "REM-2",
                    "fecha_display": "10/08/2026",
                }
            ]

        mock_recolectar.side_effect = _side_effect
        payload = construir_analisis_trazabilidad_articulo(
            "empresa92",
            615,
            fecha_desde="2026-08-01",
            fecha_hasta="2026-08-31",
        )
        self.assertTrue(payload["saldo_inicial"]["calculado_ok"])
        self.assertEqual(payload["saldo_inicial"]["valor"], 100)
        self.assertEqual(payload["saldo_inicial"]["origen"], "historico_pre_periodo")
        self.assertEqual(len(payload["movimientos"]), 1)
        self.assertEqual(payload["movimientos"][0]["codigo_movimiento"], 2)
        self.assertEqual(payload["movimientos"][0]["saldo_corrido"], 80)
        self.assertEqual(payload["kpis"]["saldo_final"], 80)
        # Eje Semi por defecto para componentes.
        self.assertEqual(mock_recolectar.call_args_list[0].kwargs.get("id_deposito"), 3)


class TestEventosMprNoAlteranSaldoKardex(SimpleTestCase):
    """Envío/parte MPR no mueven stock_deposito; no entran al saldo corrido."""

    @patch("mpr.services_kardex_articulo._consultar_movimientos_inventario_mstock", return_value=[])
    @patch("mpr.services_kardex_articulo._consultar_movimientos_stock_rem_fa", return_value=[])
    @patch("mpr.services_kardex_articulo._consultar_movimientos_kardex_articulo", return_value=[])
    def test_recolectar_sin_eventos_mpr(self, *_mocks):
        from mpr.services_kardex_articulo import _recolectar_movimientos_analisis

        with patch(
            "mpr.services_kardex_articulo._consultar_eventos_mpr_articulo",
            return_value=[{"tipo": "envio", "cantidad": 999, "fecha_sort": "2026-08-01"}],
        ):
            movs = _recolectar_movimientos_analisis(
                "empresa92",
                1401,
                id_deposito=6,
                fecha_desde="2026-07-01",
                fecha_hasta="2026-09-30",
            )
        self.assertEqual(movs, [])


class TestComponenteUsaDepositoSemiPorDefecto(SimpleTestCase):
    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Semi elaborado")
    @patch("mpr.services.get_deposito_semi_elaborado_mpr", return_value=3)
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=0)
    @patch("mpr.services.get_bom_detalle", return_value=None)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=0)
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={1401: ("610", "Componente prueba")},
    )
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis", return_value=[])
    def test_componente_sin_filtro_explicito_usa_semi(self, mock_recolectar, *_mocks):
        payload = construir_analisis_trazabilidad_articulo(
            "empresa92",
            1401,
            fecha_desde="2026-07-01",
            fecha_hasta="2026-09-30",
        )
        self.assertEqual(payload["deposito"]["id"], 3)
        self.assertEqual(payload["deposito"]["tipo_eje"], "semi")
        self.assertEqual(mock_recolectar.call_args_list[0].kwargs.get("id_deposito"), 3)


class TestGoldenSampleKardex610Blanco(SimpleTestCase):
    """Paridad con exports/kardex_610_t6_terminado.xlsx · hoja Kardex Blanco (1399)."""

    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Terminado")
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=0)
    @patch("mpr.services.get_bom_detalle", return_value=None)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=25)
    @patch(
        "mpr.services.listar_demanda_ped_por_articulo",
        return_value=[
            {
                "codigo_movimiento_pedido": 9603,
                "cantidad_pendiente_prod": 120,
                "nro_pedido": "0008-00000225",
                "nombre_cliente": "901 mabel salinas",
                "fecha": "18/08/2026",
            }
        ],
    )
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=-130)
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={1399: ("610-BL", "610 T6 Kamp Tripack Blanco 3P")},
    )
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis")
    def test_secuencia_opa_faltante_rem_cierra_en_terminado_negativo(
        self, mock_recolectar, *_mocks
    ):
        def _side_effect(*_args, **kwargs):
            if kwargs.get("solo_pre_periodo"):
                return []
            return [
                {
                    "fecha_sort": date(2026, 7, 30),
                    "fecha_display": "30/07/2026",
                    "codigo_movimiento": 3802,
                    "entrada": 130,
                    "salida": 0,
                    "afecta_deposito": True,
                    "clase_ui": "opa",
                    "nro_comprobante": "0001-00002181",
                    "detalle": "Armado 1ra MPR",
                    "fuente": "mstock",
                },
                {
                    "fecha_sort": date(2026, 8, 5),
                    "fecha_display": "05/08/2026",
                    "codigo_movimiento": 6181,
                    "entrada": 0,
                    "salida": 130,
                    "afecta_deposito": True,
                    "clase_ui": "inventario",
                    "nro_comprobante": "0001-00004229",
                    "detalle": "Inventario físico campaña #3",
                    "fuente": "mstock",
                },
                {
                    "fecha_sort": date(2026, 8, 26),
                    "fecha_display": "26/08/2026",
                    "codigo_movimiento": 12584,
                    "entrada": 0,
                    "salida": 130,
                    "afecta_deposito": True,
                    "clase_ui": "rem",
                    "nro_comprobante": "0008-00000321",
                    "detalle": "Remito Salida",
                    "fuente": "stock",
                },
                {
                    "fecha_sort": date(2026, 8, 26),
                    "fecha_display": "26/08/2026",
                    "codigo_movimiento": 12588,
                    "entrada": 0,
                    "salida": 130,
                    "afecta_deposito": False,
                    "clase_ui": "fa",
                    "nro_comprobante": "0008-00000302",
                    "detalle": "Venta",
                    "fuente": "stock",
                },
            ]

        mock_recolectar.side_effect = _side_effect
        payload = construir_analisis_trazabilidad_articulo(
            "administranet",
            1399,
            fecha_desde="2026-07-01",
            fecha_hasta="2026-09-01",
        )
        movs = payload["movimientos"]
        self.assertEqual([m["clase_ui"] for m in movs], ["opa", "inventario", "rem"])
        self.assertEqual([m["saldo_corrido"] for m in movs], [130, 0, -130])
        self.assertEqual(payload["kpis"]["saldo_final"], -130)
        self.assertEqual(payload["stock"]["terminado"], -130)
        self.assertEqual(payload["demanda_ped"]["totales"]["p_ped"], 120)
        self.assertEqual(payload["deposito"]["id"], 6)


class TestArticulo340StockInicialRemSobrante(SimpleTestCase):
    """Regresión artículo 340: Stock Inicial +167, REM −167, Sobrante +167 → cierre 167."""

    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Terminado")
    @patch("mpr.services.get_deposito_terminado_mpr", return_value=6)
    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=0)
    @patch("mpr.services.get_bom_detalle", return_value={"componentes": []})
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=99)
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=167)
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={340: ("610", "610 T4 Kamp Tripack Bl/Gm/Ne 3P")},
    )
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis")
    def test_cierra_en_stock_terminado_sin_advertencia_descuadre(self, mock_recolectar, *_mocks):
        def _side_effect(*_args, **kwargs):
            if kwargs.get("solo_pre_periodo"):
                return []
            return [
                {
                    "fecha_sort": date(2026, 7, 23),
                    "fecha_display": "23/07/2026",
                    "codigo_movimiento": 1181,
                    "entrada": 167,
                    "salida": 0,
                    "afecta_deposito": True,
                    "clase_ui": "stock_inicial",
                    "nro_comprobante": "0001-00001181",
                    "detalle": "Stock Inicial",
                    "fuente": "mstock",
                },
                {
                    "fecha_sort": date(2026, 8, 4),
                    "fecha_display": "04/08/2026",
                    "codigo_movimiento": 4508,
                    "entrada": 0,
                    "salida": 167,
                    "afecta_deposito": True,
                    "clase_ui": "rem",
                    "nro_comprobante": "0008-00000143",
                    "detalle": "610 T4 Kamp Tripack Bl/Gm/Ne 3P",
                    "fuente": "stock",
                },
                {
                    "fecha_sort": date(2026, 8, 5),
                    "fecha_display": "05/08/2026",
                    "codigo_movimiento": 6182,
                    "entrada": 167,
                    "salida": 0,
                    "afecta_deposito": True,
                    "clase_ui": "inventario",
                    "nro_comprobante": "0001-00004230",
                    "detalle": "Inventario físico campaña #3",
                    "fuente": "mstock",
                },
            ]

        mock_recolectar.side_effect = _side_effect
        payload = construir_analisis_trazabilidad_articulo(
            "administranet1",
            340,
            fecha_desde="2026-07-01",
            fecha_hasta="2026-09-30",
        )
        movs = payload["movimientos"]
        self.assertEqual([m["clase_ui"] for m in movs], ["stock_inicial", "rem", "inventario"])
        self.assertEqual([m["saldo_corrido"] for m in movs], [167, 0, 167])
        self.assertEqual(movs[-1]["conteo"], 167)
        self.assertEqual(payload["kpis"]["saldo_final"], 167)
        self.assertFalse(
            any("no coincide" in a.lower() for a in payload.get("advertencias", []))
        )
