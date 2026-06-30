"""Tests imputación Armado 1ra — FIFO, límites, permiso."""
import json
from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase

from mpr.services import confirmar_imputacion_armado, sugerir_imputacion_fifo
from mpr.views import (
    ImputacionArmado1raView,
    ImputacionArmadoConfirmarAPIView,
    ImputacionArmadoSugerirAPIView,
)


class ConfirmarImputacionTest(SimpleTestCase):
    @patch("mpr.services._actualizar_estado_imputacion_movimiento")
    @patch("mpr.models.MprImputacionArmado")
    @patch("mpr.services.get_connection")
    @patch("mpr.services._cantidad_imputada_mstock", return_value=3)
    @patch("mpr.models.MprArmadoSurtidoMovimiento")
    def test_rechaza_exceder_cantidad_armada(self, mock_mov_cls, *_mocks):
        mov = MagicMock()
        mov.modo = "1ra"
        mov.cantidad_packs = 5
        mov.id_articulo_pack = 100
        mock_mov_cls.objects.get.return_value = mov

        ok, err = confirmar_imputacion_armado(
            "emp",
            99,
            [{"codigo_movimiento_pedido": 1000, "cantidad": 3, "origen_regla": "MANUAL"}],
            1,
        )
        self.assertFalse(ok)
        self.assertIn("No puede imputar", err or "")


class SugerirFifoTest(SimpleTestCase):
    @patch("mpr.services._listar_demanda_abierta_fifo")
    @patch("mpr.services._cantidad_imputada_mstock", return_value=0)
    @patch("mpr.models.MprArmadoSurtidoMovimiento")
    def test_fifo_asigna_pedido_mas_antiguo_primero(self, mock_mov_cls, *_mocks):
        mov = MagicMock()
        mov.cantidad_packs = 10
        mov.id_articulo_pack = 200
        mock_mov_cls.objects.get.return_value = mov
        _listar_demanda = _mocks[1]
        _listar_demanda.return_value = [
            {
                "codigo_movimiento_pedido": 1,
                "cantidad_pendiente_prod": 4,
                "nro_pedido": "P-A",
                "nombre_cliente": "Cliente A",
                "fecha": "01/01/2026",
                "id_lista_detalle": 10,
                "id_lista_produccion": 5,
            },
            {
                "codigo_movimiento_pedido": 2,
                "cantidad_pendiente_prod": 8,
                "nro_pedido": "P-B",
                "nombre_cliente": "Cliente B",
                "fecha": "02/01/2026",
                "id_lista_detalle": 11,
                "id_lista_produccion": 6,
            },
        ]
        lineas, err = sugerir_imputacion_fifo("emp", 50)
        self.assertIsNone(err)
        self.assertEqual(len(lineas), 2)
        self.assertEqual(lineas[0]["codigo_movimiento_pedido"], 1)
        self.assertEqual(lineas[0]["cantidad"], 4)
        self.assertEqual(lineas[1]["cantidad"], 6)


class ImputacionPermisoTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_403_sin_permiso_imputacion(self):
        request = self.factory.get("/mpr/imputacion-armado-1ra/")
        request.session = {"user": {"id_usuario": 1}}
        user = MagicMock(is_authenticated=True)
        user.is_admin.return_value = False
        user.cod_usuario = "operario"
        user.roles.all.return_value = []
        user.tiene_permiso.return_value = False
        request.user = user
        with self.assertRaises(PermissionDenied):
            ImputacionArmado1raView.as_view()(request)

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch("mpr.views.listar_mstock_pendientes_imputacion", return_value=[])
    def test_api_sugerir_requiere_permiso(self, *_mocks):
        request = self.factory.get(
            "/mpr/api/imputacion-armado-1ra/sugerir/",
            {"codigo_movimiento": "10"},
        )
        request.session = {"user": {"id_usuario": 1}}
        user = MagicMock(is_authenticated=True)
        user.is_admin.return_value = False
        user.cod_usuario = "operario"
        user.roles.all.return_value = []
        user.tiene_permiso.return_value = False
        request.user = user
        with self.assertRaises(PermissionDenied):
            ImputacionArmadoSugerirAPIView.as_view()(request)


class ImputacionPedidoContextoTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.views.sugerir_imputacion_fifo", return_value=([], None))
    @patch("mpr.views.listar_mstock_pendientes_imputacion")
    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_filtro_lote_precarga_primer_mstock(self, _base, mock_listar, _fifo):
        lote_id = "05b57525-7890-1234-abcd-ef0123456789"
        mock_listar.return_value = [
            {
                "codigo_movimiento": 30,
                "id_lote_armado": lote_id,
                "cantidad_pendiente_imputar": 10,
            },
        ]
        request = self.factory.get(
            f"/mpr/imputacion-armado-1ra/?id_lote_armado={lote_id}"
        )
        request.session = {"user": {"id_usuario": 1}}
        user = MagicMock(is_authenticated=True)
        user.is_admin.return_value = True
        request.user = user
        response = ImputacionArmado1raView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        mock_listar.assert_called_once_with(
            "emp", filtros={"id_lote_armado": lote_id}
        )
        self.assertEqual(response.context_data["lote_armado_sel"], lote_id)
        self.assertEqual(response.context_data["codigo_movimiento_sel"], 30)
        self.assertTrue(response.context_data["filtrado_por_lote"])


class ImputacionConfirmarApiTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.views.confirmar_imputacion_armado", return_value=(True, None))
    @patch("mpr.views.sugerir_imputacion_fifo")
    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_confirmar_fifo_ok(self, _base, mock_fifo, mock_confirmar):
        mock_fifo.return_value = (
            [{"codigo_movimiento_pedido": 1000, "cantidad": 6, "origen_regla": "FIFO"}],
            None,
        )
        request = self.factory.post(
            "/mpr/api/imputacion-armado-1ra/confirmar/",
            data=json.dumps({"codigo_movimiento": 30, "usar_fifo": True}),
            content_type="application/json",
        )
        request.session = {"user": {"id_usuario": 1}}
        user = MagicMock(is_authenticated=True)
        user.is_admin.return_value = True
        request.user = user
        response = ImputacionArmadoConfirmarAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("cantidad_imputada"), 6)
        mock_confirmar.assert_called_once()

    @patch("mpr.views.sugerir_imputacion_fifo", return_value=([], "No hay demanda"))
    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_confirmar_fifo_sin_demanda(self, _base, _fifo):
        request = self.factory.post(
            "/mpr/api/imputacion-armado-1ra/confirmar/",
            data=json.dumps({"codigo_movimiento": 30, "usar_fifo": True}),
            content_type="application/json",
        )
        request.session = {"user": {"id_usuario": 1}}
        user = MagicMock(is_authenticated=True)
        user.is_admin.return_value = True
        request.user = user
        response = ImputacionArmadoConfirmarAPIView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertFalse(payload.get("ok"))

    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_confirmar_api_requiere_permiso(self, _base):
        request = self.factory.post(
            "/mpr/api/imputacion-armado-1ra/confirmar/",
            data=json.dumps({"codigo_movimiento": 30}),
            content_type="application/json",
        )
        request.session = {"user": {"id_usuario": 1}}
        user = MagicMock(is_authenticated=True)
        user.is_admin.return_value = False
        user.cod_usuario = "operario"
        user.roles.all.return_value = []
        user.tiene_permiso.return_value = False
        request.user = user
        with self.assertRaises(PermissionDenied):
            ImputacionArmadoConfirmarAPIView.as_view()(request)


class DemandaDetallePkTest(SimpleTestCase):
    def test_pendiente_por_pk_legacy_id_lista_produccion(self):
        from mpr.services import _demanda_detalle_pendiente_actual

        cursor = MagicMock()
        cursor.fetchone.return_value = (7,)
        pend = _demanda_detalle_pendiente_actual(
            cursor,
            "lista_produccion_detalle",
            "id_lista_produccion",
            id_fila=42,
        )
        self.assertEqual(pend, 7)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("id_lista_produccion", sql)
        self.assertNotIn("LIMIT 1", sql)

    def test_pendiente_suma_sin_pk(self):
        from mpr.services import _demanda_detalle_pendiente_actual

        cursor = MagicMock()
        cursor.fetchone.return_value = (12,)
        pend = _demanda_detalle_pendiente_actual(
            cursor,
            "lista_produccion_detalle",
            "id_lista_detalle",
            codigo_movimiento_pedido=1000,
            id_articulo=200,
        )
        self.assertEqual(pend, 12)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("SUM", sql.upper())

    def test_pendiente_fallback_suma_si_pk_sin_pendiente(self):
        from mpr.services import _demanda_detalle_pendiente_actual

        cursor = MagicMock()
        cursor.fetchone.side_effect = [(0,), (15,)]
        pend = _demanda_detalle_pendiente_actual(
            cursor,
            "lista_produccion_detalle",
            "id_lista_detalle",
            id_fila=99,
            codigo_movimiento_pedido=1000,
            id_articulo=200,
        )
        self.assertEqual(pend, 15)
        self.assertEqual(cursor.execute.call_count, 2)

    @patch("mpr.services.columna_existe", return_value=True)
    @patch("mpr.services.columna_primary_key", return_value="id_lista_produccion")
    def test_pk_fila_usa_primary_key_real(self, _pk, _existe):
        from mpr.services import _mpr_columna_pk_fila_lista_produccion_detalle

        col = _mpr_columna_pk_fila_lista_produccion_detalle(MagicMock(), "lista_produccion_detalle")
        self.assertEqual(col, "id_lista_produccion")
