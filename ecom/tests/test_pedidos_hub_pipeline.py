"""Tests pipeline hub Lista|Kanban."""

from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from ecom.models import EcomCart, EcomCartItem, EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.pedidos_hub_pipeline import (
    _columna_lote_desde_contexto,
    _columna_ped_mysql,
    _etiqueta_sucursal,
    _mapa_reverso_lotes,
    _masivos_anulados,
    _pedidos_mysql,
    archivar_borrador_masivo,
    columnas_hub_visibles,
    construir_hub_pedidos,
    eliminar_borrador_masivo_definitivo,
    es_ped_migracion_best,
    url_pedido_masivo_modo_simple,
    url_pedido_masivo_readonly,
    url_resumen_lote_masivo,
)


class TestUrlPedidoMasivoModoSimple(TestCase):
    def test_con_cod_mov(self):
        url = url_pedido_masivo_modo_simple(cod_mov=12345)
        self.assertIn("modo=simple", url)
        self.assertIn("cod_mov=12345", url)
        self.assertIn("/pedido-masivo-sucursales/", url)

    def test_con_consulta(self):
        url = url_pedido_masivo_modo_simple(cod_mov=99, consulta=True)
        self.assertIn("modo=simple", url)
        self.assertIn("cod_mov=99", url)
        self.assertIn("consulta=1", url)

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
        self.assertNotIn("consulta=1", url)


class TestEsPedMigracionBest(TestCase):
    def test_nro_best(self):
        self.assertTrue(es_ped_migracion_best("BEST-12345"))
        self.assertTrue(es_ped_migracion_best("best-99"))

    def test_tipo_pedido(self):
        self.assertTrue(es_ped_migracion_best(tipo_pedido="Migracion BEST"))
        self.assertTrue(es_ped_migracion_best(tipo_pedido="  migracion best  "))

    def test_ped_comercial_no_es_best(self):
        self.assertFalse(es_ped_migracion_best("0001-00000555", "Ecom vendedor"))

    def test_detalle_cutover_best(self):
        self.assertTrue(
            es_ped_migracion_best(
                "0001-00000003",
                "Sistema",
                "Cutover BEST orden 5001",
            )
        )
        self.assertTrue(
            es_ped_migracion_best(detalle="Migrado desde BEST orden 123")
        )

    def test_detalle_sin_marcador_no_es_best(self):
        self.assertFalse(
            es_ped_migracion_best("0001-00000003", "Sistema", "Pedido cliente")
        )


class TestPedMysqlBestConsulta(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_ped_best_url_consulta(self, mock_cursor_ctx, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 777,
                "NroComprobante": "BEST-777",
                "tipo_pedido": "Migracion BEST",
                "detalle": "Cutover BEST orden 777",
                "fecha": "23/07/2026",
                "Estado": "Pendiente",
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "id_cliente": 10,
                "nombre_cliente": "Cliente BEST",
                "ImporteVenta": Decimal("500"),
                "total_calc": Decimal("500"),
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

        mock_cursor_ctx.side_effect = _fake_cursor

        items = _pedidos_mysql("emp_hub", {"todos_clientes": "Si"})
        self.assertEqual(len(items), 1)
        self.assertIn("consulta=1", items[0]["url"])
        self.assertIn("cod_mov=777", items[0]["url"])

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_ped_normal_sin_consulta(self, mock_cursor_ctx, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 888,
                "NroComprobante": "0001-00000888",
                "tipo_pedido": "Ecom vendedor",
                "detalle": "",
                "fecha": "23/07/2026",
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

        mock_cursor_ctx.side_effect = _fake_cursor

        items = _pedidos_mysql("emp_hub", {"todos_clientes": "Si"})
        self.assertEqual(len(items), 1)
        self.assertNotIn("consulta=1", items[0]["url"])

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_ped_remediado_best_consulta_por_detalle(self, mock_cursor_ctx, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 999,
                "NroComprobante": "0001-00000003",
                "tipo_pedido": "Sistema",
                "detalle": "Cutover BEST orden 5001",
                "fecha": "23/07/2026",
                "Estado": "Pendiente",
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "id_cliente": 10,
                "nombre_cliente": "Cliente BEST remediado",
                "ImporteVenta": Decimal("500"),
                "total_calc": Decimal("500"),
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

        mock_cursor_ctx.side_effect = _fake_cursor

        items = _pedidos_mysql("emp_hub", {"todos_clientes": "Si"})
        self.assertEqual(len(items), 1)
        self.assertIn("consulta=1", items[0]["url"])
        self.assertIn("cod_mov=999", items[0]["url"])


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
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_incluye_sucursal_e_importe_venta(self, mock_cursor_ctx, _apr):
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

    def test_eliminar_draft_anulado(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=7,
            id_cliente=2,
            estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
        )
        pk = d.pk
        ok, msg = eliminar_borrador_masivo_definitivo(pk, 7, "emp_hub")
        self.assertTrue(ok)
        self.assertEqual(msg, "Borrador eliminado definitivamente.")
        self.assertFalse(EcomPedidoMasivoDraft.objects.filter(pk=pk).exists())

    def test_rechazar_eliminar_borrador_activo(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=7,
            id_cliente=2,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        ok, msg = eliminar_borrador_masivo_definitivo(d.pk, 7, "emp_hub")
        self.assertFalse(ok)
        self.assertIn("anulados", msg.lower())
        self.assertTrue(EcomPedidoMasivoDraft.objects.filter(pk=d.pk).exists())

    def test_rechazar_eliminar_confirmado(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=7,
            id_cliente=2,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMADO,
        )
        ok, msg = eliminar_borrador_masivo_definitivo(d.pk, 7, "emp_hub")
        self.assertFalse(ok)
        self.assertIn("anulados", msg.lower())
        self.assertTrue(EcomPedidoMasivoDraft.objects.filter(pk=d.pk).exists())

    def test_eliminar_draft_otro_usuario(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=7,
            id_cliente=2,
            estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
        )
        ok, msg = eliminar_borrador_masivo_definitivo(d.pk, 99, "emp_hub")
        self.assertFalse(ok)
        self.assertEqual(msg, "Borrador no encontrado.")
        self.assertTrue(EcomPedidoMasivoDraft.objects.filter(pk=d.pk).exists())

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
        self.assertTrue(items[0]["meta"].get("puede_eliminar_definitivo"))

    @patch("ecom.services.pedidos_hub_pipeline._nombres_clientes", return_value={4: "Simple SA"})
    def test_masivos_anulados_modo_simple(self, _nombres):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=9,
            id_cliente=4,
            estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
            modo=EcomPedidoMasivoDraft.MODO_SIMPLE,
        )
        items = _masivos_anulados("emp_hub", 9)
        self.assertEqual(len(items), 1)
        self.assertIn("Pedido simple", items[0]["titulo"])
        self.assertIn("modo=simple", items[0]["url"])
        self.assertIn(f"draft={d.pk}", items[0]["url"])


class TestPedidosMysqlAlcance(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial", return_value=[10, 20, 21])
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_vendedor_filtra_por_alcance(self, mock_cursor_ctx, mock_alcance, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        _pedidos_mysql(
            "emp_hub",
            {"id_vendedor_usr": 10, "synap_permisos": [], "nombre_puesto": "Vendedor"},
        )
        mock_alcance.assert_called_once()
        sql = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]
        self.assertIn("CodViajante IN", sql)
        self.assertEqual(params[:3], [10, 20, 21])
        self.assertEqual(params[3], 5000)

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial", return_value=[10])
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_sin_dias_no_filtra_fecha(self, mock_cursor_ctx, _alcance, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        _pedidos_mysql("emp_hub", {"todos_clientes": "Si"}, dias=None)
        sql = cursor.execute.call_args[0][0]
        self.assertNotIn("DATE_SUB", sql)
        self.assertNotIn("cp.Fecha >=", sql)

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_con_dias_si_filtra_fecha(self, mock_cursor_ctx, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        _pedidos_mysql("emp_hub", {"todos_clientes": "Si"}, dias=30)
        sql = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]
        self.assertIn("DATE_SUB", sql)
        self.assertIn("cp.Fecha >=", sql)
        self.assertEqual(params[0], 30)

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial")
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_ver_todos_legacy_sin_filtro_viajante(self, mock_cursor_ctx, mock_alcance, _apr):
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
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial")
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_puesto_supervisor_sin_filtro_viajante(self, mock_cursor_ctx, mock_alcance, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        for puesto in ("Supervisor", "Supervisor venta", "Administracion"):
            mock_alcance.reset_mock()
            _pedidos_mysql(
                "emp_hub",
                {
                    "nombre_puesto": puesto,
                    "todos_clientes": "No",
                    "synap_permisos": [],
                    "id_vendedor_usr": 1,
                },
            )
            mock_alcance.assert_not_called()
            sql = cursor.execute.call_args[0][0]
            self.assertNotIn("CodViajante IN", sql, msg=puesto)
            self.assertNotIn("1 = 0", sql, msg=puesto)

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial", return_value=[])
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_alcance_vacio_sin_resultados(self, mock_cursor_ctx, _alcance, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = []

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        items = _pedidos_mysql("emp_hub", {"id_vendedor_usr": 10, "nombre_puesto": "Vendedor"})
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


class TestCargasMasivasPipeline(TestCase):
    def _draft_confirmado(self, *, id_usuario=22, codigos=None, estado_lote="-"):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_hub",
            id_usuario=id_usuario,
            id_cliente=5,
            cod_viajante=10,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMADO,
            codigos_movimiento=codigos or [101, 102],
            estado_aprobacion_lote=estado_lote,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d,
            id_articulo=1,
            id_cliente_domicilio=10,
            cantidad_packs=Decimal("2"),
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d,
            id_articulo=2,
            id_cliente_domicilio=20,
            cantidad_packs=Decimal("1"),
        )
        return d

    @patch("ecom.services.pedidos_hub_pipeline.puede_aprobar_lote", return_value=True)
    @patch("ecom.services.pedidos_hub_pipeline._fetch_estados_pedidos_lote")
    @patch("ecom.services.pedidos_hub_pipeline._nombres_clientes", return_value={5: "Mayorista SA"})
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql")
    def test_construir_hub_lote_en_columna_operativa(
        self,
        mock_pedidos,
        _apr,
        _nombres,
        mock_estados,
        _puede_lote,
    ):
        mock_pedidos.return_value = []
        mock_estados.return_value = {
            101: {
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "Estado": "Pendiente",
                "estado_aprobacion_comercial": "pendiente",
            },
            102: {
                "Anulado": "Si",
                "autorizacion": "Autorizado",
                "Estado": "Pendiente",
                "estado_aprobacion_comercial": "pendiente",
            },
        }
        draft = self._draft_confirmado(estado_lote="pendiente")
        hub = construir_hub_pedidos(
            "emp_hub",
            {"id_usuario": 22, "todos_clientes": "Si", "synap_permisos": ["ecom.pedidos.aprobar"]},
        )
        self.assertEqual(hub["cargas_masivas"], [])
        tarjeta = next(it for it in hub["items"] if it.get("tipo") == "lote_masivo")
        self.assertEqual(tarjeta["columna"], "por_autorizar")
        col_por_aut = next(c for c in hub["columnas"] if c["id"] == "por_autorizar")
        self.assertTrue(any(it.get("id_ref") == f"lote-{draft.pk}" for it in col_por_aut["items"]))
        self.assertEqual(tarjeta["tipo"], "lote_masivo")
        self.assertIn("Mayorista SA", tarjeta["titulo"])
        self.assertIn("2 sucursales", tarjeta["subtitulo"])
        self.assertIn("1/2 activos", tarjeta["subtitulo"])
        self.assertEqual(tarjeta["url"], url_pedido_masivo_readonly(draft.pk))
        self.assertEqual(tarjeta["meta"]["draft_id"], draft.pk)
        self.assertEqual(tarjeta["meta"]["estado_aprobacion_lote"], "pendiente")
        self.assertTrue(tarjeta["meta"]["puede_aprobar_lote"])
        ids_columnas = [c["id"] for c in hub["columnas"]]
        self.assertNotIn("cargas_masivas", ids_columnas)
        self.assertFalse(any(it.get("meta", {}).get("lote_draft_id") for it in hub["items"]))

    @patch("ecom.services.pedidos_hub_pipeline.puede_aprobar_lote", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline._fetch_estados_pedidos_lote")
    @patch("ecom.services.pedidos_hub_pipeline._nombres_clientes", return_value={5: "Mayorista SA"})
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql")
    def test_construir_hub_filtra_ped_hijos_de_lote(
        self,
        mock_pedidos,
        _apr,
        _nombres,
        mock_estados,
        _puede_lote,
    ):
        mock_pedidos.return_value = [
            {
                "tipo": "ped",
                "columna": "enviado",
                "titulo": "PED 101",
                "subtitulo": "Mayorista SA",
                "fecha": "22/07/2026",
                "url": "/ped/",
                "id_ref": "ped-101",
                "meta": {"lote_draft_id": 99, "codigo_movimiento": 101},
            },
            {
                "tipo": "ped",
                "columna": "enviado",
                "titulo": "PED 555",
                "subtitulo": "Cliente suelto",
                "fecha": "22/07/2026",
                "url": "/ped/",
                "id_ref": "ped-555",
                "meta": {"codigo_movimiento": 555},
            },
        ]
        mock_estados.return_value = {
            101: {
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "Estado": "Pendiente",
                "estado_aprobacion_comercial": "-",
            },
        }
        self._draft_confirmado(codigos=[101])
        hub = construir_hub_pedidos(
            "emp_hub",
            {"id_usuario": 22, "todos_clientes": "Si"},
        )
        ids_ref = {it.get("id_ref") for it in hub["items"]}
        self.assertNotIn("ped-101", ids_ref)
        self.assertIn("ped-555", ids_ref)
        self.assertTrue(any(it.get("tipo") == "lote_masivo" for it in hub["items"]))

    def test_columna_lote_desde_contexto_prioridades(self):
        ids = columnas_hub_visibles(aprobacion_activa=True)
        ctx_pendiente = {
            "estado_aprobacion_lote": "pendiente",
            "n_total": 2,
            "k_activos": 2,
            "rollup": {"por_autorizar": 2},
        }
        self.assertEqual(
            _columna_lote_desde_contexto(ctx_pendiente, aprobacion_on=True, ids_visibles=ids),
            "por_autorizar",
        )
        ctx_anulado = {
            "estado_aprobacion_lote": "-",
            "n_total": 2,
            "k_activos": 0,
            "rollup": {"anulado": 2},
        }
        self.assertEqual(
            _columna_lote_desde_contexto(ctx_anulado, aprobacion_on=True, ids_visibles=ids),
            "anulado",
        )
        ctx_en_curso = {
            "estado_aprobacion_lote": "aprobado",
            "n_total": 2,
            "k_activos": 2,
            "rollup": {"en_curso": 1, "enviado": 1},
        }
        self.assertEqual(
            _columna_lote_desde_contexto(ctx_en_curso, aprobacion_on=True, ids_visibles=ids),
            "en_curso",
        )
        ctx_cerrado = {
            "estado_aprobacion_lote": "aprobado",
            "n_total": 2,
            "k_activos": 2,
            "rollup": {"cerrado": 2},
        }
        self.assertEqual(
            _columna_lote_desde_contexto(ctx_cerrado, aprobacion_on=True, ids_visibles=ids),
            "cerrado",
        )
        ids_sin_apr = columnas_hub_visibles(aprobacion_activa=False)
        ctx_por_aut = {
            "estado_aprobacion_lote": "-",
            "n_total": 1,
            "k_activos": 1,
            "rollup": {"por_autorizar": 1},
        }
        self.assertEqual(
            _columna_lote_desde_contexto(ctx_por_aut, aprobacion_on=False, ids_visibles=ids_sin_apr),
            "enviado",
        )

    @patch("ecom.services.pedidos_hub_pipeline._fetch_estados_pedidos_lote", return_value={})
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=True)
    def test_mapa_reverso_resuelve_mismo_draft(self, _apr, _estados):
        self._draft_confirmado(codigos=[101, 102])
        mapa, ctx = _mapa_reverso_lotes(
            "emp_hub",
            22,
            {"id_usuario": 22, "todos_clientes": "Si"},
            aprobacion_on=True,
        )
        self.assertEqual(mapa[101], mapa[102])
        draft_id = mapa[101]
        self.assertEqual(ctx[draft_id]["indice_por_cod"][101], 1)
        self.assertEqual(ctx[draft_id]["indice_por_cod"][102], 2)

    @patch("ecom.services.pedidos_hub_pipeline.alcance_viajantes_comercial", return_value=[99])
    @patch("ecom.services.pedidos_hub_pipeline._fetch_estados_pedidos_lote", return_value={})
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    def test_lote_fuera_de_alcance_no_aparece(self, _apr, _estados, _alcance):
        self._draft_confirmado(id_usuario=22, codigos=[201])
        mapa, _ctx = _mapa_reverso_lotes(
            "emp_hub",
            77,
            {"id_usuario": 77, "id_vendedor_usr": 99, "nombre_puesto": "Vendedor"},
            aprobacion_on=False,
        )
        self.assertEqual(mapa, {})

    @patch("ecom.services.pedidos_hub_pipeline.puede_aprobar_pedido", return_value=True)
    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=True)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_ped_hijo_enriquecido_y_sin_aprobar_si_lote_pendiente(
        self,
        mock_cursor_ctx,
        _apr,
        _puede_ped,
    ):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 101,
                "NroComprobante": "0001-00000101",
                "fecha": "22/07/2026",
                "Estado": "Pendiente",
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "id_cliente": 5,
                "nombre_cliente": "Mayorista SA",
                "ImporteVenta": Decimal("500"),
                "total_calc": Decimal("500"),
                "id_cliente_domicilio": 10,
                "calle_domicilio": "Calle",
                "nro_domicilio": "1",
                "CodViajante": 10,
                "estado_aprobacion_comercial": "pendiente",
            }
        ]

        @contextmanager
        def _fake_cursor(*_a, **_kw):
            yield cursor

        mock_cursor_ctx.side_effect = _fake_cursor

        mapa = {101: 7}
        contexto = {
            7: {
                "draft_id": 7,
                "id_cliente": 5,
                "nombre_cliente": "Mayorista SA",
                "n_total": 2,
                "indice_por_cod": {101: 1, 102: 2},
                "estado_aprobacion_lote": "pendiente",
            }
        }
        items = _pedidos_mysql(
            "emp_hub",
            {"todos_clientes": "Si", "synap_permisos": ["ecom.pedidos.aprobar"]},
            aprobacion_on=True,
            mapa_lotes=mapa,
            contexto_lotes=contexto,
        )
        self.assertEqual(len(items), 1)
        meta = items[0]["meta"]
        self.assertEqual(meta["lote_draft_id"], 7)
        self.assertEqual(meta["lote_label"], "Lote · Mayorista SA (1/2)")
        self.assertEqual(meta["lote_indice"], 1)
        self.assertEqual(meta["lote_total"], 2)
        self.assertFalse(meta["puede_aprobar"])

    @patch("ecom.services.pedidos_hub_pipeline.aprobacion_pedidos_activa", return_value=False)
    @patch("ecom.services.pedidos_hub_pipeline.mysql_cursor")
    def test_ped_suelto_sin_meta_lote(self, mock_cursor_ctx, _apr):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 555,
                "NroComprobante": "0001-00000555",
                "fecha": "22/07/2026",
                "Estado": "Pendiente",
                "Anulado": "No",
                "autorizacion": "Autorizado",
                "id_cliente": 5,
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

        mock_cursor_ctx.side_effect = _fake_cursor

        items = _pedidos_mysql("emp_hub", {"todos_clientes": "Si"})
        meta = items[0]["meta"]
        self.assertNotIn("lote_draft_id", meta)
        self.assertNotIn("lote_label", meta)
