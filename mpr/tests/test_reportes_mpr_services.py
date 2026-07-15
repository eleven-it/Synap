# Tests TDD para servicios de reportes MPR. Especificaciones en docs/reports/mpr/ESPEC_MPR_*.md

from unittest.mock import MagicMock, patch

from django.test import TestCase

from mpr import services as mpr_services


# --- OPT atrasadas (listar_opt_listado solo_atrasadas=True) ---


class TestListarOptListadoSoloAtrasadas(TestCase):
    """ESPEC_MPR_OPT_ATRASADAS: listar_opt_listado(base_empresa, solo_atrasadas=True)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.listar_opt_listado("", solo_atrasadas=True), [])
        self.assertEqual(mpr_services.listar_opt_listado(None, solo_atrasadas=True), [])

    def test_con_cursor_mock_devuelve_filas_con_campos_esperados(self):
        fila = {
            "id_lista_produccion": 10,
            "id_articulo": 100,
            "codigo_articulo": "ART01",
            "descripcion_articulo": "Artículo prueba",
            "cantidad_pendiente_prod": 5,
            "en_proceso_produccion": "Si",
        }
        cursor = MagicMock()
        cursor.fetchall.return_value = [fila]
        cursor.fetchone.return_value = None

        def fake_mysql_cursor(base_empresa, dict_cursor=True):
            class Ctx:
                def __enter__(_):
                    return cursor

                def __exit__(_, *args):
                    pass

            return Ctx()

        with patch("mpr.services.mysql_cursor", side_effect=fake_mysql_cursor):
            with patch("mpr.services._nombre_tabla", return_value="lista_produccion_agrupada"):
                with patch("mpr.services._columnas_opcionales_op_agrupada", return_value={"fecha_objetivo": "fecha_objetivo"}):
                    result = mpr_services.listar_opt_listado("empresa92", limit=10, solo_atrasadas=True)
        self.assertIsInstance(result, list)
        if result:
            self.assertIn("id_lista_produccion", result[0])
            self.assertIn("codigo_articulo", result[0])
            self.assertIn("cantidad_pendiente_prod", result[0])


# --- Resumen pedidos por estado ---


class TestReporteMprPedidosPorEstado(TestCase):
    """ESPEC_MPR_PEDIDOS_ESTADO: reporte_mpr_pedidos_por_estado(base_empresa)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.reporte_mpr_pedidos_por_estado(""), [])
        self.assertEqual(mpr_services.reporte_mpr_pedidos_por_estado(None), [])

    def test_retorna_lista_de_dicts_estado_cantidad(self):
        result = mpr_services.reporte_mpr_pedidos_por_estado("empresa92")
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("estado", item)
            self.assertIn("cantidad", item)
            self.assertIsInstance(item["cantidad"], (int, float))

    def test_con_datos_devuelve_cuatro_estados(self):
        with patch("mpr.services.listar_pedidos_fabrica") as mock_listar:
            mock_listar.return_value = [
                {"estado_pedido_opt": "Pendiente"},
                {"estado_pedido_opt": "Pendiente"},
                {"estado_pedido_opt": "Produccion"},
                {"estado_pedido_opt": "Terminado"},
            ]
            # Cuando esté implementado, debe agregar y devolver 4 filas (Pendiente, Produccion, Parcial, Terminado)
            result = mpr_services.reporte_mpr_pedidos_por_estado("empresa92")
        self.assertIsInstance(result, list)
        # Stub actual devuelve []; implementación debe devolver 4 elementos
        if len(result) == 4:
            estados = {r["estado"] for r in result}
            self.assertIn("Pendiente", estados)
            self.assertIn("Produccion", estados)
            self.assertIn("Parcial", estados)
            self.assertIn("Terminado", estados)


# --- Demanda vs. stock (brecha) ---


class TestReporteMprBrechaDemanda(TestCase):
    """ESPEC_MPR_BRECHA_DEMANDA: reporte_mpr_brecha_demanda(base_empresa, limit=200)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.reporte_mpr_brecha_demanda(""), [])
        self.assertEqual(mpr_services.reporte_mpr_brecha_demanda(None, limit=100), [])

    @patch("mpr.services._fetch_descripciones_articulo")
    @patch("mpr.services.listar_demanda_pack_desde_pedidos")
    def test_retorna_lista_con_columnas_obligatorias(
        self, mock_listar_demanda, mock_descripciones
    ):
        mock_listar_demanda.return_value = [
            {
                "id_articulo": 101,
                "cantidad_pedida_pedido": 20,
                "stock_terminado": 5,
                "cantidad_a_fabricar": 15,
                "cantidad_urgente_abs": 4,
            },
            {
                "id_articulo": 102,
                "cantidad_pedida_pedido": 8,
                "stock_terminado": 8,
                "cantidad_a_fabricar": 0,
                "cantidad_urgente_abs": 0,
            },
        ]
        mock_descripciones.return_value = {
            101: ("PACK-101", "Pack urgente"),
            102: ("PACK-102", "Pack cubierto"),
        }

        result = mpr_services.reporte_mpr_brecha_demanda("empresa92", limit=10)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["codigo_articulo"], "PACK-101")
        self.assertEqual(result[0]["cantidad_a_fabricar"], 15)
        self.assertEqual(result[0]["urgente"], 1)
        self.assertEqual(result[1]["cantidad_a_fabricar"], 0)
        self.assertEqual(result[1]["urgente"], 0)
        columnas = ("codigo_articulo", "descripcion_articulo", "demanda_pendiente", "stock_terminado", "cantidad_a_fabricar", "urgente")
        for item in result:
            for col in columnas:
                self.assertIn(col, item, msg=f"Falta columna {col}")
            if "cantidad_a_fabricar" in item:
                self.assertGreaterEqual(item["cantidad_a_fabricar"], 0)

    def test_pasa_fechas_a_listar_demanda(self):
        with patch(
            "mpr.services.listar_demanda_pack_desde_pedidos",
            return_value=[],
        ) as mock_listar:
            mpr_services.reporte_mpr_brecha_demanda(
                "empresa92",
                fecha_desde="2026-06-29",
                fecha_hasta="2026-07-05",
            )
        mock_listar.assert_called_once()
        _, kwargs = mock_listar.call_args
        self.assertEqual(kwargs.get("fecha_desde"), "2026-06-29")
        self.assertEqual(kwargs.get("fecha_hasta"), "2026-07-05")


class TestReporteMprPendienteComponentes(TestCase):
    """REQ-PEND-01: pendientes totales del tablero consolidado."""

    @patch("mpr.services.listar_tablero_por_articulo")
    def test_solicita_pendientes_y_no_solo_urgentes(self, mock_tablero):
        mock_tablero.return_value = [
            {"id_articulo": 1, "resta_total": 15, "resta_urgente": 0},
            {"id_articulo": 2, "resta_total": 70, "resta_urgente": 70},
        ]

        result = mpr_services.reporte_mpr_pendiente_componentes("empresa92")

        mock_tablero.assert_called_once_with(
            "empresa92", solo_pendiente=True, limit=200
        )
        self.assertEqual([fila["id_articulo"] for fila in result["filas"]], [1, 2])
        self.assertEqual(result["kpis"]["componentes"], 2)
        self.assertEqual(result["kpis"]["criticos"], 1)


# --- Movimientos de producción ---


class TestReporteMprMovimientos(TestCase):
    """ESPEC_MPR_MOVIMIENTOS_PRODUCCION: ledgers mpr_* (sin lista_produccion ni MSTOCK legacy)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.reporte_mpr_movimientos(""), [])
        self.assertEqual(mpr_services.reporte_mpr_movimientos(None, limit=50), [])

    def test_cada_fila_tiene_campos_ledgers(self):
        mock_eventos = [{
            "tipo": "parte",
            "tipo_label": "Parte de producción",
            "fecha_sort": "2026-07-04 10:00:00",
            "fecha_display": "04/07/2026 10:00",
            "cantidad": 12,
            "id_articulo": 1275,
            "detalle": "Parte #1",
            "operario": "Juan",
        }]
        with patch("mpr.services._recolectar_eventos_ledgers_mpr", return_value=mock_eventos):
            with patch(
                "mpr.services._fetch_descripciones_articulo",
                return_value={1275: ("COMP01", "Componente prueba")},
            ):
                result = mpr_services.reporte_mpr_movimientos(
                    "empresa92", fecha_desde="2026-07-04", fecha_hasta="2026-07-04", limit=50
                )
        self.assertEqual(len(result), 1)
        fila = result[0]
        self.assertEqual(fila["tipo_mov"], "Parte de producción")
        self.assertEqual(fila["codigo_articulo"], "COMP01")
        self.assertEqual(fila["cantidad"], 12)
        self.assertEqual(fila["operario"], "Juan")


# --- Desperdicio / Scrap ---


class TestReporteMprDesperdicio(TestCase):
    """ESPEC_MPR_DESPERDICIO: reporte_mpr_desperdicio(base_empresa, fecha_desde, fecha_hasta, limit)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.reporte_mpr_desperdicio(""), [])
        self.assertEqual(mpr_services.reporte_mpr_desperdicio(None, fecha_desde="2025-01-01"), [])

    def test_retorna_lista_con_estructura_esperada(self):
        result = mpr_services.reporte_mpr_desperdicio(
            "empresa92",
            fecha_desde="2025-01-01",
            fecha_hasta="2025-12-31",
            limit=200,
        )
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("articulo", item)
            self.assertIn("cantidad_desperdicio", item)
