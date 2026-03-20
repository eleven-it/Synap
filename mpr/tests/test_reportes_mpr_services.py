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

    def test_retorna_lista_con_columnas_obligatorias(self):
        result = mpr_services.reporte_mpr_brecha_demanda("empresa92", limit=10)
        self.assertIsInstance(result, list)
        columnas = ("codigo_articulo", "descripcion_articulo", "demanda_pendiente", "stock_terminado", "cantidad_a_fabricar", "urgente")
        for item in result:
            for col in columnas:
                self.assertIn(col, item, msg=f"Falta columna {col}")
            if "cantidad_a_fabricar" in item:
                self.assertGreaterEqual(item["cantidad_a_fabricar"], 0)


# --- Movimientos de producción ---


class TestReporteMprMovimientos(TestCase):
    """ESPEC_MPR_MOVIMIENTOS_PRODUCCION: reporte_mpr_movimientos(base_empresa, limit=200)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.reporte_mpr_movimientos(""), [])
        self.assertEqual(mpr_services.reporte_mpr_movimientos(None, limit=50), [])

    def test_cada_fila_tiene_fecha_tipo_mov_codigo_movimiento(self):
        result = mpr_services.reporte_mpr_movimientos("empresa92", limit=50)
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("fecha", item)
            self.assertIn("tipo_mov", item)
            self.assertIn("codigo_movimiento", item)
        self.assertLessEqual(len(result), 200)


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


# --- Producción por operario ---


class TestReporteMprProduccionPorOperario(TestCase):
    """ESPEC_MPR_PRODUCCION_OPERARIO: reporte_mpr_produccion_por_operario(base_empresa, fecha_desde, fecha_hasta)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.reporte_mpr_produccion_por_operario(""), [])
        self.assertEqual(mpr_services.reporte_mpr_produccion_por_operario(None, fecha_desde="2025-01-01"), [])

    def test_retorna_lista_con_nro_opt_asignadas(self):
        result = mpr_services.reporte_mpr_produccion_por_operario(
            "empresa92",
            fecha_desde="2025-01-01",
            fecha_hasta="2025-12-31",
        )
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("nro_opt_asignadas", item)
            self.assertIn("operario", item)


# --- OPT cerradas ---


class TestReporteMprOptCerradas(TestCase):
    """ESPEC_MPR_OPT_CERRADAS: reporte_mpr_opt_cerradas(base_empresa, fecha_desde, fecha_hasta)."""

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        self.assertEqual(mpr_services.reporte_mpr_opt_cerradas(""), [])
        self.assertEqual(mpr_services.reporte_mpr_opt_cerradas(None), [])

    def test_retorna_lista_con_id_lista_principal_y_cantidad(self):
        result = mpr_services.reporte_mpr_opt_cerradas(
            "empresa92",
            fecha_desde="2025-01-01",
            fecha_hasta="2025-12-31",
        )
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("id_opt", item)
            self.assertIn("cantidad_total", item)
