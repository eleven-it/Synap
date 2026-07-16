"""Tests Phase 4 — matriz pedido masivo (catálogo filtrado + autoguardado)."""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.pedido_masivo_views import (
    PedidoMasivoCeldaAPIView,
    PedidoMasivoDescuentoFilaAPIView,
    PedidoMasivoPreviewAPIView,
)
from ecom.services.pedido_masivo_matriz import (
    anular_borrador_masivo_usuario,
    asegurar_descuento_fila_articulo,
    buscar_articulos_filtrados_ternas,
    eliminar_fila_articulo,
    guardar_celda,
    guardar_descuento_fila,
    guardar_descuento_pie,
    marcas_asignadas_viajante_cliente,
    obtener_o_crear_draft,
    serializar_matriz,
)


class _User:
    is_authenticated = True
    is_superuser = True

    def tiene_permiso(self, _c):
        return True


class TestGuardarCelda(TestCase):
    def test_upsert_y_cero_elimina(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        ok, _, payload = guardar_celda(
            d, id_articulo=5, id_cliente_domicilio=3, cantidad_packs="2.5"
        )
        self.assertTrue(ok)
        self.assertEqual(d.celdas.count(), 1)
        self.assertEqual(payload["cantidad_packs"], "2.5")

        ok2, _, payload2 = guardar_celda(
            d, id_articulo=5, id_cliente_domicilio=3, cantidad_packs=0
        )
        self.assertTrue(ok2)
        self.assertTrue(payload2["eliminada"])
        self.assertEqual(d.celdas.count(), 0)

    def test_eliminar_fila_articulo_quita_celdas_y_descuento(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            descuentos_fila={"9": 5.0, "8": 2.0},
        )
        guardar_celda(d, id_articulo=9, id_cliente_domicilio=1, cantidad_packs=3)
        guardar_celda(d, id_articulo=9, id_cliente_domicilio=2, cantidad_packs=4)
        guardar_celda(d, id_articulo=8, id_cliente_domicilio=1, cantidad_packs=1)
        self.assertEqual(d.celdas.filter(id_articulo=9).count(), 2)

        ok, msg = eliminar_fila_articulo(d, id_articulo=9)
        self.assertTrue(ok, msg)
        d.refresh_from_db()
        self.assertEqual(d.celdas.filter(id_articulo=9).count(), 0)
        self.assertEqual(d.celdas.filter(id_articulo=8).count(), 1)
        self.assertNotIn("9", d.descuentos_fila or {})
        self.assertIn("8", d.descuentos_fila or {})


class TestObtenerDraft(TestCase):
    def test_reutiliza_borrador_mismo_cliente(self):
        d1, _ = obtener_o_crear_draft(
            base_empresa="emp_m",
            id_usuario=7,
            id_cliente=20,
            cod_viajante=3,
        )
        d2, _ = obtener_o_crear_draft(
            base_empresa="emp_m",
            id_usuario=7,
            id_cliente=20,
            cod_viajante=3,
        )
        self.assertEqual(d1.pk, d2.pk)

    def test_abrir_anulado_reactiva_borrador(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=7,
            id_cliente=20,
            estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
        )
        opened, err = obtener_o_crear_draft(
            base_empresa="emp_m",
            id_usuario=7,
            id_cliente=20,
            cod_viajante=3,
            draft_id=d.pk,
        )
        self.assertIsNotNone(opened, err)
        opened.refresh_from_db()
        self.assertEqual(opened.estado, EcomPedidoMasivoDraft.ESTADO_BORRADOR)


class TestAnularBorradorMasivo(TestCase):
    def test_anular_solo_desde_borrador(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        ok, msg = anular_borrador_masivo_usuario(d.pk, 1, "emp_m")
        self.assertTrue(ok, msg)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_ANULADO)

    def test_anular_confirmando_trata_como_borrador(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        )
        ok, _ = anular_borrador_masivo_usuario(d.pk, 1, "emp_m")
        self.assertTrue(ok)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_ANULADO)

    def test_no_anular_confirmado(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMADO,
        )
        ok, msg = anular_borrador_masivo_usuario(d.pk, 1, "emp_m")
        self.assertFalse(ok)
        self.assertIn("edición", msg.lower())


class TestCatalogoFiltrado(TestCase):
    @patch(
        "ecom.services.pedido_masivo_matriz.marcas_asignadas_viajante_cliente",
        return_value=[11, 12],
    )
    @patch("ecom.services.pedido_masivo_matriz.leer_contexto_cliente_masivo")
    @patch("ecom.services.pedido_masivo_matriz.calcular_precio_articulo_row", return_value=Decimal("85"))
    @patch("ecom.services.pedido_masivo_matriz.resolver_reglas_precio_map", return_value={})
    @patch("ecom.services.pedido_masivo_matriz.get_mysql_pool")
    def test_busqueda_liviana_terminado(
        self, mock_pool, mock_reglas, _precio, mock_ctx, mock_marcas
    ):
        mock_ctx.return_value = {
            "descRenglon": Decimal("8"),
            "descPie": Decimal("5"),
            "lista_id": 1,
        }
        cur = mock_pool.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value
        cur.fetchall.return_value = [(9, "2401", "Calcetín Negro")]
        cur.description = [("IDArt",), ("id_manual",), ("nombre",)]
        r = buscar_articulos_filtrados_ternas(
            "emp_m", cod_viajante=1, id_cliente=2, id_cliente_domicilio=9, q="2401"
        )
        self.assertFalse(r["sin_marcas"])
        mock_marcas.assert_called_once_with("emp_m", 1, 2, 9)
        self.assertEqual(r["items"][0]["id_manual"], "2401")
        self.assertEqual(r["items"][0]["nombre"], "Calcetín Negro")
        self.assertEqual(r["items"][0]["precio_unitario_neto"], 85.0)
        self.assertEqual(r["items"][0]["precio_lista1"], 85.0)
        sql = cur.execute.call_args[0][0]
        self.assertIn("tipo_art_fab", sql)
        self.assertIn("Terminado", sql)
        self.assertIn("ecommerce = 'Si'", sql)
        self.assertIn("Discontinuo = 'No'", sql)
        self.assertIn("Precio1V", sql)
        mock_reglas.assert_called_once()

    @patch(
        "ecom.services.pedido_masivo_matriz.marcas_asignadas_viajante_cliente",
        return_value=[11],
    )
    @patch("ecom.services.pedido_masivo_matriz.leer_contexto_cliente_masivo")
    @patch("ecom.services.pedido_masivo_matriz.calcular_precio_articulo_row", return_value=Decimal("10"))
    @patch("ecom.services.pedido_masivo_matriz.resolver_reglas_precio_map", return_value={})
    @patch("ecom.services.pedido_masivo_matriz.get_mysql_pool")
    def test_listar_todos_sin_q(
        self, mock_pool, mock_reglas, _precio, mock_ctx, _marcas
    ):
        mock_ctx.return_value = {
            "descRenglon": Decimal("0"),
            "descPie": Decimal("0"),
            "lista_id": 1,
        }
        cur = mock_pool.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value
        cur.fetchall.return_value = [(1, "100", "Art A"), (2, "200", "Art B")]
        cur.description = [("IDArt",), ("id_manual",), ("nombre",)]
        r = buscar_articulos_filtrados_ternas(
            "emp_m", cod_viajante=1, id_cliente=2, q="", listar_todos=True, tam=5000
        )
        self.assertEqual(len(r["items"]), 2)
        sql = cur.execute.call_args[0][0]
        self.assertNotIn("id_manual LIKE", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(cur.execute.call_args[0][1][-1], 5000)

    @patch(
        "ecom.services.pedido_masivo_matriz.marcas_asignadas_viajante_cliente",
        return_value=[],
    )
    def test_sin_marcas_vacio(self, _m):
        r = buscar_articulos_filtrados_ternas("emp_m", cod_viajante=1, id_cliente=2)
        self.assertTrue(r["sin_marcas"])
        self.assertEqual(r["items"], [])


class TestMarcasPorSucursal(TestCase):
    @patch("ecom.services.pedido_masivo_matriz.get_mysql_pool")
    def test_union_sin_sucursal(self, mock_pool):
        cur = mock_pool.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value
        cur.fetchall.return_value = [(11,), (12,)]
        marcas = marcas_asignadas_viajante_cliente("emp_m", 1, 2, None)
        self.assertEqual(marcas, [11, 12])
        sql = cur.execute.call_args[0][0]
        self.assertIn("DISTINCT CodMarca", sql)
        self.assertNotIn("id_cliente_domicilio =", sql)

    @patch("ecom.services.pedido_masivo_matriz.get_mysql_pool")
    def test_filtra_por_sucursal(self, mock_pool):
        cur = mock_pool.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value
        cur.fetchall.return_value = [(7,)]
        marcas = marcas_asignadas_viajante_cliente("emp_m", 1, 2, 9)
        self.assertEqual(marcas, [7])
        sql = cur.execute.call_args[0][0]
        self.assertIn("id_cliente_domicilio =", sql)
        self.assertEqual(cur.execute.call_args[0][1], [1, 2, 9])


class TestSerializarMatriz(TestCase):
    @patch(
        "ecom.services.pedido_masivo_matriz.listar_sucursales_cliente",
        return_value=[{"id_cliente_domicilio": 9, "etiqueta": "Suc A"}],
    )
    @patch("ecom.services.pedido_masivo_matriz.leer_contexto_cliente_masivo")
    @patch("ecom.services.pedido_masivo_matriz._nombres_articulos")
    def test_celdas_mapa(self, mock_n, mock_ctx, _s):
        mock_ctx.return_value = {
            "descRenglon": Decimal("8"),
            "descPie": Decimal("5"),
            "lista_id": 2,
        }
        mock_n.return_value = {
            4: {
                "codigo": "X",
                "descripcion": "Art X",
                "precio_unitario_neto": 85.0,
                "precio_lista1": 85.0,
            }
        }
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
            descuentos_fila={"4": 10.0},
            descuento_pie_pct=Decimal("5"),
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d,
            id_articulo=4,
            id_cliente_domicilio=9,
            cantidad_packs=Decimal("3"),
        )
        m = serializar_matriz(d, "emp_m")
        self.assertEqual(m["celdas"]["4:9"], "3")
        self.assertEqual(m["articulos"][0]["codigo"], "X")
        self.assertEqual(m["articulos"][0]["precio_unitario_neto"], 85.0)
        self.assertEqual(m["articulos"][0]["porcentaje_descuento"], 10.0)
        self.assertEqual(m["desc_pie_pct"], 5.0)
        self.assertEqual(m["descuentos_fila"]["4"], 10.0)
        self.assertEqual(len(m["sucursales"]), 1)

    @patch(
        "ecom.services.pedido_masivo_matriz.listar_sucursales_cliente",
        return_value=[
            {"id_cliente_domicilio": 9, "etiqueta": "Suc A"},
            {"id_cliente_domicilio": 12, "etiqueta": "Suc B"},
        ],
    )
    @patch("ecom.services.pedido_masivo_matriz.leer_contexto_cliente_masivo")
    @patch("ecom.services.pedido_masivo_matriz._nombres_articulos")
    def test_modo_simple_una_columna_fija(self, mock_n, mock_ctx, _s):
        mock_ctx.return_value = {
            "descRenglon": Decimal("0"),
            "descPie": Decimal("0"),
            "lista_id": 1,
        }
        mock_n.return_value = {
            4: {
                "codigo": "X",
                "descripcion": "Art X",
                "precio_unitario_neto": 10.0,
                "precio_lista1": 10.0,
            }
        }
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
            modo=EcomPedidoMasivoDraft.MODO_SIMPLE,
            id_domicilio_fijo=9,
            cod_mov_origen=7001,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d,
            id_articulo=4,
            id_cliente_domicilio=9,
            cantidad_packs=Decimal("1"),
        )
        m = serializar_matriz(d, "emp_m")
        self.assertEqual(m["modo"], "simple")
        self.assertEqual(m["cod_mov_origen"], 7001)
        self.assertEqual(m["id_domicilio_fijo"], 9)
        self.assertEqual(len(m["sucursales"]), 1)
        self.assertEqual(m["sucursales"][0]["id_cliente_domicilio"], 9)
        self.assertEqual(m["celdas"]["4:9"], "1")


class TestApiCelda(TestCase):
    @patch("ecom.pedido_masivo_views._session_base_empresa", return_value="emp_m")
    def test_post_guarda(self, _b):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=55,
            id_cliente=1,
        )
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/pedido-masivo/celda/",
            {
                "draft_id": d.pk,
                "id_articulo": 8,
                "id_cliente_domicilio": 2,
                "cantidad_packs": "1",
            },
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp_m", "id_usuario": 55}}
        force_authenticate(req, user=_User())
        resp = PedidoMasivoCeldaAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(d.celdas.count(), 1)


class TestDescuentosMasivo(TestCase):
    @patch(
        "ecom.services.pedido_masivo_matriz.leer_contexto_cliente_masivo",
        return_value={
            "descRenglon": Decimal("8"),
            "descPie": Decimal("5"),
            "lista_id": 1,
        },
    )
    def test_precarga_desc_renglon_al_celda(self, _ctx):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
        )
        guardar_celda(d, id_articulo=7, id_cliente_domicilio=3, cantidad_packs="2")
        d.refresh_from_db()
        self.assertEqual(d.descuentos_fila.get("7"), 8.0)

    def test_guardar_descuento_fila_y_pie(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
        )
        ok, _ = guardar_descuento_fila(
            d, id_articulo=5, porcentaje_descuento=12
        )
        self.assertTrue(ok)
        ok2, _ = guardar_descuento_pie(d, desc_pie_pct=7)
        self.assertTrue(ok2)
        d.refresh_from_db()
        self.assertEqual(d.descuentos_fila.get("5"), 12.0)
        self.assertEqual(d.descuento_pie_pct, Decimal("7"))


class TestApiPreviewMasivo(TestCase):
    @patch("ecom.pedido_masivo_views._resolver_cabecera_masivo")
    @patch("ecom.pedido_masivo_views.calcular_totales_lote_masivo")
    @patch("ecom.pedido_masivo_views._session_base_empresa", return_value="emp_m")
    def test_preview_ok_con_warning(self, _b, mock_preview, mock_cab):
        from ecom.services.pedido_cabecera_comercial import PedidoCabeceraComercial
        from datetime import date

        mock_cab.return_value = (
            PedidoCabeceraComercial(
                fecha_pedido=date.today(),
                fecha_entrega=None,
                vencimiento=date.today(),
                id_condventa=1,
                cond_venta="Contado",
                lista_id=1,
            ),
            None,
        )
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=55,
            id_cliente=1,
        )
        mock_preview.return_value = {
            "ok": True,
            "sucursales": [{"id_cliente_domicilio": 2, "neto": 900.0, "iva": 189.0, "total": 1089.0}],
            "total_lote": {"neto": 900.0, "iva": 189.0, "total": 1089.0},
            "warning": "La matriz tiene 250 celdas con cantidad (límite recomendado 200).",
            "preview_incompleto": False,
            "celdas_con_cantidad": 250,
        }
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/pedido-masivo/preview/",
            {"draft_id": d.pk, "desc_pie_pct": 5},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp_m", "id_usuario": 55}}
        force_authenticate(req, user=_User())
        resp = PedidoMasivoPreviewAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertIn("warning", resp.data)
        self.assertEqual(resp.data["total_lote"]["total"], 1089.0)


class TestApiDescuentoFila(TestCase):
    @patch("ecom.pedido_masivo_views._session_base_empresa", return_value="emp_m")
    @patch("ecom.pedido_masivo_views.serializar_matriz", return_value={"draft_id": 1})
    def test_post_descuento_fila(self, _m, _b):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=55,
            id_cliente=1,
        )
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/pedido-masivo/descuento-fila/",
            {"draft_id": d.pk, "id_articulo": 3, "porcentaje_descuento": 15},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp_m", "id_usuario": 55}}
        force_authenticate(req, user=_User())
        resp = PedidoMasivoDescuentoFilaAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        d.refresh_from_db()
        self.assertEqual(d.descuentos_fila.get("3"), 15.0)
