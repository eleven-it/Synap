"""Tests pipeline hub Lista|Kanban."""

from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from ecom.models import EcomCart, EcomCartItem, EcomPedidoMasivoDraft
from ecom.services.pedidos_hub_pipeline import (
    _columna_ped_mysql,
    _etiqueta_sucursal,
    _masivos_anulados,
    _pedidos_mysql,
    archivar_borrador_masivo,
    columnas_hub_visibles,
    construir_hub_pedidos,
    url_pedido_masivo_modo_simple,
)


class TestUrlPedidoMasivoModoSimple(TestCase):
    def test_con_cod_mov(self):
        url = url_pedido_masivo_modo_simple(cod_mov=12345)
        self.assertIn("modo=simple", url)
        self.assertIn("cod_mov=12345", url)
        self.assertIn("/pedido-masivo-sucursales/", url)

    def test_con_draft(self):
        url = url_pedido_masivo_modo_simple(draft=99)
        self.assertIn("modo=simple", url)
        self.assertIn("draft=99", url)

    def test_ped_mysql_url_modo_simple(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 555,
                "NroComprobante": "0001-00000555",
                "fecha": "16/07/2026",
                "Estado": "Pendiente",
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "id_cliente": 10,
                "nombre_cliente": "Cliente X",
                "ImporteVenta": Decimal("100"),
                "total_calc": Decimal("100"),
                "id_cliente_domicilio": 5,
                "calle_domicilio": "Calle",
                "nro_domicilio": "1",
                "CodViajante": 1,
                "estado_aprobacion_comercial": "-",
            }
        ]

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        with patch(
            "ecom.services.pedidos_hub_pipeline.workflow_jerarquia_comercial_activo",
            return_value=False,
        ), patch(
            "ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa",
            return_value=False,
        ), patch(
            "ecom.services.pedidos_hub_pipeline.mysql_cursor",
            side_effect=_fake_cursor,
        ):
            items = _pedidos_mysql("emp_hub", {"todos_clientes": "Si"})
        self.assertEqual(len(items), 1)
        url = items[0]["url"]
        self.assertIn("modo=simple", url)
        self.assertIn("cod_mov=555", url)


class TestColumnaPed(TestCase):
    def test_clasificacion_sin_aprobacion(self):
        self.assertEqual(_columna_ped_mysql("Si", "No Autorizado", "Pendiente"), "anulado")
        # Crédito "No Autorizado" no abre columna Por autorizar si aprobación off.
        self.assertEqual(_columna_ped_mysql("No", "No Autorizado", "Pendiente"), "enviado")
        self.assertEqual(_columna_ped_mysql("No", "Autorizado", "Pendiente"), "enviado")
        self.assertEqual(_columna_ped_mysql("No", "Autorizado", "En preparación"), "en_curso")
        self.assertEqual(_columna_ped_mysql("No", "Autorizado", "Facturado"), "cerrado")
        self.assertEqual(_columna_ped_mysql("No", "Autorizado", "Entregado"), "cerrado")

    def test_clasificacion_comercial_activa(self):
        self.assertEqual(
            _columna_ped_mysql(
                "No",
                "Autorizado",
                "Pendiente",
                estado_aprobacion_comercial="pendiente",
                aprobacion_activa=True,
            ),
            "por_autorizar",
        )
        self.assertEqual(
            _columna_ped_mysql(
                "No",
                "No Autorizado",
                "Pendiente",
                estado_aprobacion_comercial="-",
                aprobacion_activa=True,
            ),
            "por_autorizar",
        )
        self.assertEqual(
            _columna_ped_mysql(
                "No",
                "Autorizado",
                "Pendiente",
                estado_aprobacion_comercial="aprobado",
                aprobacion_activa=True,
            ),
            "enviado",
        )
        self.assertEqual(
            _columna_ped_mysql(
                "No",
                "Autorizado",
                "En preparación",
                estado_aprobacion_comercial="aprobado",
                aprobacion_activa=True,
            ),
            "en_curso",
        )
        self.assertEqual(
            _columna_ped_mysql(
                "No",
                "Autorizado",
                "Preparado",
                estado_aprobacion_comercial="aprobado",
                aprobacion_activa=True,
            ),
            "en_curso",
        )


class TestColumnasVisibles(TestCase):
    def test_sin_aprobacion_oculta_por_autorizar_y_aprobado(self):
        ids = columnas_hub_visibles(aprobacion_activa=False)
        self.assertNotIn("por_autorizar", ids)
        self.assertNotIn("aprobado", ids)
        self.assertEqual(
            list(ids),
            ["borrador", "enviado", "en_curso", "cerrado", "anulado"],
        )

    def test_con_aprobacion_incluye_cola(self):
        ids = columnas_hub_visibles(aprobacion_activa=True)
        self.assertIn("por_autorizar", ids)
        self.assertIn("aprobado", ids)
        self.assertIn("en_curso", ids)
        self.assertIn("cerrado", ids)


class TestEtiquetaSucursal(TestCase):
    def test_calle_nro(self):
        self.assertEqual(_etiqueta_sucursal("Av. Corrientes", "1234", 10), "Av. Corrientes 1234")

    def test_fallback_id(self):
        self.assertEqual(_etiqueta_sucursal("", "", 42), "Sucursal #42")


class TestPedidosMysql(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline.workflow_jerarquia_comercial_activo", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_incluye_sucursal_e_importe_venta(self, mock_cursor_ctx, _apr, _wf):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 9001,
                "NroComprobante": "0001-00001234",
                "fecha": "14/07/2026",
                "Estado": "Pendiente",
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "id_cliente": 613,
                "nombre_cliente": "Distribuidora Norte",
                "ImporteVenta": Decimal("1500.50"),
                "total_calc": Decimal("1400.00"),
                "id_cliente_domicilio": 77,
                "calle_domicilio": "San Martín",
                "nro_domicilio": "500",
            }
        ]

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        items = _pedidos_mysql("emp_hub", {"todos_clientes": "Si"})
        self.assertEqual(len(items), 1)
        tarjeta = items[0]
        self.assertEqual(tarjeta["sucursal"], "San Martín 500")
        self.assertIn("Distribuidora Norte", tarjeta["subtitulo"])
        self.assertIn("1,500.50", tarjeta["subtitulo"])
        self.assertEqual(tarjeta["meta"]["id_cliente_domicilio"], 77)
        self.assertEqual(tarjeta["meta"]["nombre_cliente"], "Distribuidora Norte")


class TestConstruirHub(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline._nombres_clientes", return_value={5: "Acme Mayorista"})
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql", return_value=[])
    def test_incluye_borradores(self, _mysql, _nombres, _apr):
        cart = EcomCart.objects.create(
            base_empresa="emp_hub",
            id_usuario=22,
            idcliente=5,
            estado=EcomCart.ESTADO_BORRADOR,
            total=Decimal("100"),
        )
        EcomCartItem.objects.create(
            cart=cart,
            id_articulo=1,
            descripcion="Art",
            cantidad=Decimal("1"),
        )
        EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=22,
            id_cliente=5,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            ultimo_error={"1": "fail"},
        )
        hub = construir_hub_pedidos(
            "emp_hub",
            {"id_usuario": 22, "todos_clientes": "Si"},
        )
        borr = next(c for c in hub["columnas"] if c["id"] == "borrador")
        self.assertGreaterEqual(borr["count"], 2)
        tipos = {i.get("tipo") for i in borr["items"]}
        self.assertIn("masivo", tipos)
        self.assertIn("carrito_legacy", tipos)
        self.assertTrue(any(i.get("badge_error") for i in borr["items"] if i.get("tipo") == "masivo"))
        self.assertEqual(hub["borradores_activos"], 1)
        titulos = [i["titulo"] for i in borr["items"]]
        self.assertTrue(any("Acme Mayorista" in t for t in titulos))
        self.assertFalse(any("cliente 5" in t for t in titulos))

    def test_archivar_draft(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=3,
            id_cliente=1,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        self.assertTrue(archivar_borrador_masivo(d.pk, 3, "emp_hub"))
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_ARCHIVADO)

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline._nombres_clientes", return_value={5: "Acme Mayorista"})
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql", return_value=[])
    def test_incluye_masivos_anulados(self, _mysql, _nombres, _apr):
        EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=22,
            id_cliente=5,
            estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
        )
        hub = construir_hub_pedidos(
            "emp_hub",
            {"id_usuario": 22, "todos_clientes": "Si"},
        )
        anul = next(c for c in hub["columnas"] if c["id"] == "anulado")
        self.assertGreaterEqual(anul["count"], 1)
        self.assertTrue(any(i.get("tipo") == "masivo" for i in anul["items"]))
        self.assertTrue(
            any("Recuperable" in (i.get("subtitulo") or "") for i in anul["items"])
        )
        self.assertTrue(
            any("Acme Mayorista" in (i.get("titulo") or "") for i in anul["items"])
        )

    @patch("ecom.services.pedidos_hub_pipeline._nombres_clientes", return_value={3: "Cliente Test"})
    def test_masivos_anulados_tarjeta(self, _nombres):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=9,
            id_cliente=3,
            estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
        )
        items = _masivos_anulados("emp_hub", 9)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["columna"], "anulado")
        self.assertIn("Cliente Test", items[0]["titulo"])
        self.assertNotIn("cliente 3", items[0]["titulo"])
        self.assertIn(f"draft={d.pk}", items[0]["url"])


class TestPedidosMysqlAlcance(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial", return_value=[10, 20, 21])
    @patch("ecom.services.pedidos_hub_pipeline.workflow_jerarquia_comercial_activo", return_value=True)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_supervisor_filtra_por_alcance(self, mock_cursor_ctx, _wf, mock_alcance, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        _pedidos_mysql(
            "emp_hub",
            {"id_vendedor_usr": 10, "synap_permisos": []},
        )
        mock_alcance.assert_called_once()
        sql = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]
        self.assertIn("CodViajante IN", sql)
        self.assertEqual(params[:3], [60, 10, 20])
        self.assertEqual(params[3], 21)

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial")
    @patch("ecom.services.pedidos_hub_pipeline.workflow_jerarquia_comercial_activo", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_ver_todos_legacy_sin_filtro_viajante(self, mock_cursor_ctx, _wf, mock_alcance, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        _pedidos_mysql("emp_hub", {"todos_clientes": "Si"})
        mock_alcance.assert_not_called()
        sql = cursor.execute.call_args[0][0]
        self.assertNotIn("CodViajante IN", sql)
        self.assertNotIn("CodViajante =", sql)

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial", return_value=[])
    @patch("ecom.services.pedidos_hub_pipeline.workflow_jerarquia_comercial_activo", return_value=True)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_alcance_vacio_sin_resultados(self, mock_cursor_ctx, _wf, _alcance, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        items = _pedidos_mysql("emp_hub", {"id_vendedor_usr": 10})
        self.assertEqual(items, [])
        sql = cursor.execute.call_args[0][0]
        self.assertIn("1 = 0", sql)


class TestConstruirHubLayoutMovil(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql", return_value=[])
    def test_incluye_layout_movil(self, _mysql, _apr):
        hub = construir_hub_pedidos("emp_hub", {"id_usuario": 1, "todos_clientes": "Si"})
        self.assertEqual(hub.get("layout_movil"), "chips_cards")

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql", return_value=[])
    def test_columnas_sin_aprobacion(self, _mysql, _apr):
        hub = construir_hub_pedidos("emp_hub", {"id_usuario": 1, "todos_clientes": "Si"})
        ids = [c["id"] for c in hub["columnas"]]
        self.assertEqual(ids, ["borrador", "enviado", "en_curso", "cerrado", "anulado"])
        self.assertNotIn("por_autorizar", hub["labels"])
        self.assertIn("cerrado", hub["labels"])
        self.assertEqual(hub["labels"]["cerrado"], "Entregado / Cerrado")

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql", return_value=[])
    def test_columnas_con_aprobacion(self, _mysql, _apr):
        hub = construir_hub_pedidos("emp_hub", {"id_usuario": 1, "todos_clientes": "Si"})
        ids = [c["id"] for c in hub["columnas"]]
        self.assertIn("por_autorizar", ids)
        self.assertIn("aprobado", ids)
        self.assertIn("en_curso", ids)
        self.assertIn("cerrado", ids)
