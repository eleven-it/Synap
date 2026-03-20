# Tests del flujo OPT (crear, detalle, liberar, OPP, armado) usando solo MySQL (lista_produccion_agrupada).
# Verifica que al dejar de usar tablas PostgreSQL (Opt/OptLinea) el flujo sigue correcto.
import os
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase, override_settings

from mpr.services import (
    get_opt_detalle,
    get_op_detalle,
    crear_opt_multiples_articulos,
    get_codigo_movimiento_opt,
)


class GetOptDetalleBaseEmpresaTest(TestCase):
    """get_opt_detalle y get_op_detalle deben devolver [] si base_empresa está vacía."""

    def test_get_opt_detalle_retorna_lista_vacia_si_base_empresa_vacia(self):
        self.assertEqual(get_opt_detalle("", 49), [])
        self.assertEqual(get_opt_detalle(None, 49), [])

    def test_get_opt_detalle_retorna_lista_vacia_si_id_lista_none(self):
        with patch("mpr.services.mysql_cursor") as mock_cursor:
            self.assertEqual(get_opt_detalle("empresa92", None), [])

    def test_get_op_detalle_retorna_lista_vacia_si_base_empresa_vacia(self):
        self.assertEqual(get_op_detalle("", 49), [])
        self.assertEqual(get_op_detalle(None, 49), [])


class GetOpDetalleMockedTest(TestCase):
    """get_op_detalle con MySQL mockeado: debe devolver la fila cuando existe."""

    def test_get_op_detalle_devuelve_linea_cuando_hay_fila_en_agrupada(self):
        fila = {
            "id_lista_produccion": 49,
            "id_articulo": 100,
            "codigo_articulo": "ART001",
            "descripcion_articulo": "Artículo prueba",
            "cantidad_pedida": 50,
            "cantidad_pendiente_prod": 50,
            "en_proceso_produccion": "Si",
            "id_operario_opt": 1,
        }
        cursor = MagicMock()
        # _nombre_tabla hace SHOW TABLES y fetchall; luego el SELECT y fetchall
        cursor.fetchall.side_effect = [
            [("lista_produccion_agrupada",), ("articulo",)],
            [("lista_produccion_agrupada",), ("articulo",)],
            [fila],
        ]
        cursor.fetchone.return_value = None

        def fake_mysql_cursor(base_empresa, dict_cursor=True):
            class Ctx:
                def __enter__(_):
                    return cursor

                def __exit__(_, *args):
                    pass

            return Ctx()

        with patch("mpr.services.mysql_cursor", side_effect=fake_mysql_cursor):
            result = get_op_detalle("empresa92", 49)
        self.assertEqual(len(result), 1, "Debe devolver una línea cuando hay fila en agrupada")
        self.assertEqual(result[0]["id_lista_produccion"], 49)
        self.assertEqual(result[0]["id_articulo"], 100)
        self.assertEqual(result[0]["en_proceso_produccion"], "Si")


class GetOptDetalleMockedTest(TestCase):
    """get_opt_detalle con MySQL mockeado: agrupa por codigo_movimiento_opt (placeholder o MSTOCK)."""

    def test_get_opt_detalle_devuelve_lineas_cuando_codigo_movimiento_opt_compartido(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"codigo_movimiento_opt": -49, "id_opt": None}
        cursor.fetchall.return_value = [{"id_lista_produccion": 49}]

        def fake_mysql_cursor(base_empresa, dict_cursor=True):
            class Ctx:
                def __enter__(_):
                    return cursor

                def __exit__(_, *args):
                    pass

            return Ctx()

        with patch("mpr.services.mysql_cursor", side_effect=fake_mysql_cursor):
            with patch("mpr.services._nombre_tabla", return_value="lista_produccion_agrupada"):
                with patch("mpr.services.get_op_detalle") as mock_get_op:
                    mock_get_op.return_value = [
                        {
                            "id_lista_produccion": 49,
                            "id_articulo": 100,
                            "cantidad_pedida": 50,
                            "cantidad_pendiente_prod": 50,
                            "en_proceso_produccion": "Si",
                        }
                    ]
                    result = get_opt_detalle("empresa92", 49)
        self.assertEqual(len(result), 1)
        mock_get_op.assert_called_once_with("empresa92", 49)


class CrearOptMultiplesArticulosMockedTest(TestCase):
    """crear_opt_multiples_articulos: actualiza agrupada/detalle en MySQL, sin usar Opt/OptLinea ORM."""

    def test_crear_opt_requiere_base_empresa_y_lineas(self):
        ok, id_lista, err = crear_opt_multiples_articulos("", None, [(100, 10, 1)])
        self.assertFalse(ok)
        self.assertIsNone(id_lista)
        self.assertIn("Base de datos", err or "")

        ok, id_lista, err = crear_opt_multiples_articulos("empresa92", None, [])
        self.assertFalse(ok)
        self.assertIsNone(id_lista)

    def test_crear_opt_intenta_actualizar_agrupada_con_operario(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [("49",)]
        cursor.fetchall.side_effect = [
            [("1",)],
            [("2",)],
        ]
        cursor.lastrowid = None

        conn = MagicMock()
        conn.cursor.return_value = cursor
        conn.autocommit = MagicMock()

        def fake_connection(base_empresa):
            class Ctx:
                def __enter__(_):
                    return conn

                def __exit__(_, *args):
                    pass

            return Ctx()

        with patch("mpr.services.get_connection", side_effect=fake_connection):
            with patch("mpr.services._nombre_tabla") as mock_tabla:
                def tablas(c, name):
                    if name == "lista_produccion_agrupada":
                        return "lista_produccion_agrupada"
                    if name == "articulo":
                        return "articulo"
                    if name == "lista_produccion_detalle":
                        return "lista_produccion_detalle"
                    if name == "comp_ped":
                        return "comp_ped"
                    return None

                mock_tabla.side_effect = tablas
                ok, id_lista, err = crear_opt_multiples_articulos(
                    "empresa92",
                    id_usuario=1,
                    lineas=[(100, 50, 5)],
                )
        # Puede fallar por validación (no hay fila en agrupada con en_proceso='No') pero no por ORM
        if ok:
            self.assertIsNotNone(id_lista)
        else:
            self.assertIn("No hay fila", err or "Actualizar")


class OptDetailViewIntegrationTest(TestCase):
    """Vista de detalle OPT: no debe 404 cuando get_opt_detalle/get_op_detalle devuelven datos."""

    def test_opt_detail_404_sin_lineas(self):
        from django.http import Http404
        from mpr.views import OptDetailView

        with patch("mpr.views.get_opt_detalle", return_value=[]):
            with patch("mpr.views.get_op_detalle", return_value=[]):
                with patch("mpr.views._get_base_empresa", return_value="empresa92"):
                    view = OptDetailView()
                    view.request = MagicMock()
                    view.request.session = {"user": {"base_empresa": "empresa92"}}
                    view.request.GET = {}
                    try:
                        view.get_context_data(id_lista=49)
                    except Http404 as e:
                        self.assertIn("OPT no encontrada", str(e))
                    else:
                        self.fail("Se esperaba Http404 cuando no hay líneas")

    def test_opt_detail_context_ok_cuando_get_opt_detalle_devuelve_linea(self):
        """Si get_opt_detalle devuelve al menos una línea, get_context_data no debe lanzar 404."""
        from mpr.views import OptDetailView

        lineas = [
            {
                "id_lista_produccion": 49,
                "id_articulo": 100,
                "codigo_articulo": "ART001",
                "descripcion_articulo": "Artículo",
                "cantidad_pedida": 50,
                "cantidad_pendiente_prod": 50,
                "en_proceso_produccion": "Si",
            }
        ]
        with patch("mpr.views.get_opt_detalle", return_value=lineas):
            with patch("mpr.views.get_op_detalle", return_value=lineas):
                with patch("mpr.views._get_base_empresa", return_value="empresa92"):
                    with patch("mpr.views.get_codigo_movimiento_opt", return_value=None):
                        with patch("mpr.views.get_id_en_abm_por_articulo", return_value=1):
                            with patch("mpr.views.get_articulo_armado_por_bom", return_value=False):
                                with patch("mpr.views.get_cantidades_armadas_por_opt", return_value={}):
                                    with patch("mpr.views.listar_opp_por_opt", return_value=[]):
                                        view = OptDetailView()
                                        view.request = MagicMock()
                                        view.request.session = {}
                                        view.request.GET = {}
                                        ctx = view.get_context_data(id_lista=49)
                                        self.assertIn("lineas", ctx)
                                        self.assertEqual(len(ctx["lineas"]), 1)
                                        self.assertEqual(ctx["opt_numero"], 49)


class GetCodigoMovimientoOptTest(TestCase):
    """get_codigo_movimiento_opt: lee desde lista_produccion_agrupada (MySQL), no desde OptLinea."""

    def test_get_codigo_movimiento_opt_base_empresa_vacia_retorna_none(self):
        self.assertIsNone(get_codigo_movimiento_opt("", 49))
        self.assertIsNone(get_codigo_movimiento_opt(None, 49))


class FlujoOptOppArmadoServiciosTest(TestCase):
    """Comprueba que los servicios del flujo OPT → Liberar → OPP → Armado existen y firma correcta (sin depender de Postgres)."""

    def test_ejecutar_liberar_opt_existe_y_retorna_tupla(self):
        from mpr.services import ejecutar_liberar_opt
        ok, cod, nro, err = ejecutar_liberar_opt(
            base_empresa="",
            id_usuario=1,
            id_lista_produccion=49,
            lineas=[],
            cantidad_total=0,
            deposito_destino=1,
        )
        self.assertFalse(ok)
        self.assertIsNone(cod)
        self.assertIsNone(nro)

    def test_ejecutar_opp_existe_y_acepta_parametros_esperados(self):
        from mpr.services import ejecutar_opp
        # Sin base_empresa o datos insuficientes debe fallar sin usar Opt/OptLinea ORM
        result = ejecutar_opp(
            base_empresa="",
            id_usuario=1,
            id_lista_produccion=49,
            lineas=[],
            cantidad_total=0,
            deposito_origen=1,
            deposito_destino=1,
        )
        self.assertIsInstance(result, (list, tuple))
        self.assertFalse(result[0] if result else True)

    def test_ejecutar_armado_existe_y_acepta_parametros_esperados(self):
        from mpr.services import ejecutar_armado
        # Llamada con datos mínimos; debe fallar por validación, no por falta de modelo
        result = ejecutar_armado(
            base_empresa="",
            id_usuario=1,
            id_en_abm=1,
            cantidad_a_armar=0,
            deposito_origen=1,
            deposito_destino=1,
        )
        self.assertIsInstance(result, (list, tuple))
        self.assertFalse(result[0] if result else True)


class ArmadoOpt89IntegracionTest(TestCase):
    """
    Test de integración: ejecutar armado contra OPT 89 en base real (MySQL).
    Se salta si no hay base configurada, OPT 89 no existe o no hay líneas armables.
    """

    def test_ejecutar_armado_opt_89_integracion(self):
        from core.mysql_pool import get_connection
        from mpr.services import (
            ejecutar_armado,
            get_deposito_semi_elaborado_mpr,
            get_deposito_terminado_mpr,
            get_lineas_armado_opt,
        )

        base_empresa = os.environ.get("MPR_TEST_BASE_EMPRESA") or getattr(
            settings, "DEFAULT_BASE_EMPRESA", None
        ) or (settings.DATABASES.get("mysql") or {}).get("NAME")
        if not base_empresa:
            self.skipTest("No hay base MySQL configurada (DEFAULT_BASE_EMPRESA / mysql.NAME).")

        try:
            with get_connection(base_empresa) as conn:
                pass
        except Exception as e:
            self.skipTest(f"No se pudo conectar a MySQL ({base_empresa}): {e}")

        lineas = get_lineas_armado_opt(base_empresa, 89)
        if not lineas:
            self.skipTest("OPT 89 no existe o no tiene líneas armables (BOM, descuenta_en=Mstock, saldo).")

        linea = lineas[0]
        id_en_abm = linea.get("id_en_abm")
        articulo_armado = linea.get("articulo_armado") or {}
        id_art_armado = articulo_armado.get("id_articulo")
        deposito_origen = get_deposito_semi_elaborado_mpr(base_empresa)
        deposito_destino = get_deposito_terminado_mpr(base_empresa)

        if not id_en_abm or not id_art_armado:
            self.skipTest("Línea de armado OPT 89 sin id_en_abm o id_articulo armado.")
        if not deposito_origen or not deposito_destino:
            self.skipTest("No hay depósito semi elaborado o terminado configurado para MPR.")

        ok, codigo_mov, nro_comp, error = ejecutar_armado(
            base_empresa=base_empresa,
            id_usuario=1,
            id_en_abm=id_en_abm,
            cantidad_a_armar=1,
            deposito_origen=deposito_origen,
            deposito_destino=deposito_destino,
            id_lista_produccion=89,
            id_articulo_armado=id_art_armado,
        )

        self.assertTrue(ok, f"Armado OPT 89 falló: {error}")
        self.assertIsNone(error or None, f"Mensaje de error no esperado: {error}")
