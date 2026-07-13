"""Tests Phase 4 — matriz pedido masivo (catálogo filtrado + autoguardado)."""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.pedido_masivo_views import PedidoMasivoCeldaAPIView
from ecom.services.pedido_masivo_matriz import (
    buscar_articulos_filtrados_ternas,
    guardar_celda,
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


class TestCatalogoFiltrado(TestCase):
    @patch("ecom.services.pedido_masivo_matriz.listar_articulos_paginado")
    @patch(
        "ecom.services.pedido_masivo_matriz.marcas_asignadas_viajante_cliente",
        return_value=[11, 12],
    )
    def test_pasa_marcas_a_listado(self, _marcas, mock_list):
        mock_list.return_value = {
            "items": [{"id_articulo": 1}],
            "total": 1,
            "pagina": 1,
            "tam": 30,
            "total_paginas": 1,
        }
        r = buscar_articulos_filtrados_ternas(
            "emp_m", cod_viajante=1, id_cliente=2, q="sock"
        )
        self.assertFalse(r["sin_marcas"])
        kwargs = mock_list.call_args.kwargs
        self.assertEqual(kwargs["filtros"]["marcas"], [11, 12])
        self.assertEqual(kwargs["filtros"]["q"], "sock")

    @patch(
        "ecom.services.pedido_masivo_matriz.marcas_asignadas_viajante_cliente",
        return_value=[],
    )
    def test_sin_marcas_vacio(self, _m):
        r = buscar_articulos_filtrados_ternas("emp_m", cod_viajante=1, id_cliente=2)
        self.assertTrue(r["sin_marcas"])
        self.assertEqual(r["items"], [])


class TestSerializarMatriz(TestCase):
    @patch(
        "ecom.services.pedido_masivo_matriz.listar_sucursales_cliente",
        return_value=[{"id_cliente_domicilio": 9, "etiqueta": "Suc A"}],
    )
    @patch(
        "ecom.services.pedido_masivo_matriz._nombres_articulos",
        return_value={4: {"codigo": "X", "descripcion": "Art X"}},
    )
    def test_celdas_mapa(self, _n, _s):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_m",
            id_usuario=1,
            id_cliente=10,
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
        self.assertEqual(len(m["sucursales"]), 1)


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
