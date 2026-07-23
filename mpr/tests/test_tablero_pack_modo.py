"""Tests — Tablero de producción: modo Pack vs Par.

Suite pura: no requiere base de datos MySQL real (usa mocks sobre las funciones
de acceso a datos).

Comando: docker exec Synap_app python manage.py test mpr.tests.test_tablero_pack_modo
"""
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase

from mpr.services import listar_tablero_pack
from mpr.views import TableroProduccionView


def _mock_filas_pack():
    """Dos packs terminados con demanda desde pedidos PED."""
    return [
        {
            "id_articulo": 1,
            "cantidad_pedida_pedido": 120.0,
            "cantidad_demanda_reserva": 24.0,
            "stock_terminado": 30.0,
            "stock_reserva": 24.0,
            "cantidad_a_fabricar": 114.0,   # max(0, 120 + 24 - 30)
            "cantidad_urgente_abs": 90.0,   # max(0, 120 - 30)
            "primera_fecha_entrega": "2026-07-15",
        },
        {
            "id_articulo": 2,
            "cantidad_pedida_pedido": 10.0,
            "cantidad_demanda_reserva": 0.0,
            "stock_terminado": 10.0,
            "stock_reserva": 0.0,
            "cantidad_a_fabricar": 5.0,
            "cantidad_urgente_abs": 0.0,     # pedido cubierto por stock terminado
            "primera_fecha_entrega": None,
        },
    ]


def _desc_map():
    return {1: ("PACK-1", "Pack Uno"), 2: ("PACK-2", "Pack Dos")}


class TestListarTableroPack(SimpleTestCase):
    """El modo Pack consolida por artículo terminado, sin explosión BOM."""

    def _call(self, *, filas_pack=None, desc_map=None, abm_map=None, bom_map=None, pedidos_map=None, **kwargs):
        if filas_pack is None:
            filas_pack = _mock_filas_pack()
        if desc_map is None:
            desc_map = _desc_map()
        if abm_map is None:
            abm_map = {}
        if bom_map is None:
            bom_map = {}
        if pedidos_map is None:
            pedidos_map = {}
        with (
            patch("mpr.services.listar_demanda_pack_desde_pedidos", return_value=filas_pack),
            patch("mpr.services._fetch_descripciones_articulo", return_value=desc_map),
            patch("mpr.services.bulk_id_en_abm", return_value=abm_map),
            patch("mpr.services.bulk_bom_detalle", return_value=bom_map),
            patch("mpr.services._tablero_pack_pedidos_revision", return_value=pedidos_map),
        ):
            return listar_tablero_pack("empresa_test", **kwargs)

    def test_mapea_columnas_a_nivel_pack(self):
        """dem_ped/dem_res/resta_* provienen del pack, sin explotar la BOM."""
        filas = self._call()
        pack1 = next(f for f in filas if f["id_articulo"] == 1)
        self.assertAlmostEqual(pack1["dem_ped"], 120.0)
        self.assertAlmostEqual(pack1["dem_res"], 24.0)
        self.assertAlmostEqual(pack1["resta_total"], 114.0)
        self.assertAlmostEqual(pack1["resta_urgente"], 90.0)
        self.assertAlmostEqual(pack1["terminado"], 30.0)
        self.assertAlmostEqual(pack1["total"], 30.0)
        self.assertEqual(pack1["codigo_manual"], "PACK-1")
        self.assertEqual(pack1["primera_fecha_entrega"], "2026-07-15")
        self.assertEqual(pack1["primera_fecha_entrega_display"], "15/07/2026")

    def test_no_ofrece_envio_a_nivel_pack(self):
        """En modo Pack, a_enviar/enviado (Fabricando) son 0: el envío es por componente."""
        filas = self._call()
        for f in filas:
            self.assertAlmostEqual(f["a_enviar"], 0.0)
            self.assertAlmostEqual(f["enviado"], 0.0)

    def test_orden_descendente_por_resta_urgente(self):
        filas = self._call()
        self.assertEqual(filas[0]["id_articulo"], 1)
        self.assertEqual(filas[1]["id_articulo"], 2)

    def test_solo_urgente_filtra_cero(self):
        """solo_urgente excluye packs sin resta urgente."""
        filas = self._call(solo_urgente=True)
        ids = [f["id_articulo"] for f in filas]
        self.assertIn(1, ids)
        self.assertNotIn(2, ids)

    def test_solo_pendiente_alias_legacy(self):
        filas = self._call(solo_pendiente=True)
        for f in filas:
            self.assertGreater(f["resta_urgente"], 0)

    def test_sin_demanda_pack_retorna_vacio(self):
        self.assertEqual(self._call(filas_pack=[]), [])

    def test_base_empresa_vacia_retorna_vacio(self):
        self.assertEqual(listar_tablero_pack(""), [])

    def test_marca_sin_receta_y_pedidos_revision(self):
        """Packs sin BOM se marcan sin_receta y traen pedidos para tooltip; no multiplica demanda."""
        pedidos = {
            1: [{
                "nro_pedido": "0001-00000032",
                "estado_pedido_opt": "Pendiente",
                "nombre_cliente": "DINOSAURIO",
                "fecha": "20/07/2026",
                "cantidad": 96,
            }]
        }
        filas = self._call(
            abm_map={2: 99},
            bom_map={99: {"componentes": [{"id_articulo": 50, "cantidad_articulo": 1}]}},
            pedidos_map=pedidos,
        )
        pack1 = next(f for f in filas if f["id_articulo"] == 1)
        pack2 = next(f for f in filas if f["id_articulo"] == 2)
        self.assertTrue(pack1["sin_receta"])
        self.assertEqual(len(pack1["pedidos_resumen"]), 1)
        self.assertIn("0001-00000032", pack1["pedidos_resumen_json"])
        self.assertFalse(pack2["sin_receta"])
        self.assertEqual(pack2["pedidos_resumen"], [])
        # La demanda sigue siendo a nivel pack (no × coef BOM).
        self.assertAlmostEqual(pack1["resta_total"], 114.0)

    def test_consulta_receta_sin_explotar_demanda(self):
        """Consulta id_en_abm/BOM solo para el flag UI; no usa explosión de componentes."""
        with (
            patch("mpr.services.listar_demanda_pack_desde_pedidos", return_value=_mock_filas_pack()),
            patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map()),
            patch("mpr.services.bulk_id_en_abm", return_value={}) as m_abm,
            patch("mpr.services.bulk_bom_detalle", return_value={}) as m_bom,
            patch("mpr.services._tablero_pack_pedidos_revision", return_value={}) as m_ped,
            patch("mpr.services._explosion_demanda_componentes_pedido_reserva_pack") as m_exp,
        ):
            listar_tablero_pack("empresa_test")
            m_abm.assert_called_once()
            m_bom.assert_not_called()  # sin id_en_abm no hay bulk_bom
            m_ped.assert_called_once()
            m_exp.assert_not_called()


class TestModoPackVsPar(SimpleTestCase):
    """La resta total pack != suma componente: el pack no multiplica por BOM."""

    def test_pack_resta_total_es_del_pack_no_del_componente(self):
        filas_pack = [{
            "id_articulo": 1,
            "cantidad_pedida_pedido": 10.0,
            "cantidad_demanda_reserva": 0.0,
            "stock_terminado": 0.0,
            "cantidad_a_fabricar": 10.0,
            "cantidad_urgente_abs": 10.0,
            "primera_fecha_entrega": None,
        }]
        with (
            patch("mpr.services.listar_demanda_pack_desde_pedidos", return_value=filas_pack),
            patch("mpr.services._fetch_descripciones_articulo", return_value={1: ("P-1", "Pack")}),
            patch("mpr.services.bulk_id_en_abm", return_value={}),
            patch("mpr.services.bulk_bom_detalle", return_value={}),
            patch("mpr.services._tablero_pack_pedidos_revision", return_value={}),
        ):
            filas = listar_tablero_pack("empresa_test")
        self.assertEqual(len(filas), 1)
        # A nivel pack, la resta total es 10 (no 10×BOM como en modo Par por componente).
        self.assertAlmostEqual(filas[0]["resta_total"], 10.0)
        self.assertEqual(filas[0]["id_articulo"], 1)
        self.assertTrue(filas[0]["sin_receta"])


class TestTableroProduccionViewModo(TestCase):
    """La vista selecciona el servicio según ?modo=par|pack (default par)."""

    def setUp(self):
        self.factory = RequestFactory()

    def _get(self, query=None):
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/mpr/tablero-produccion/", query or {})
        request.session = self.client.session
        request.user = AnonymousUser()
        view = TableroProduccionView()
        view.request = request
        return view, request

    def _run(self, query=None):
        view, request = self._get(query)
        with (
            patch("mpr.views._get_base_empresa", return_value="empresa_test"),
            patch("mpr.views._context_filtro_marcas", return_value={}),
            patch("mpr.views._usuario_puede_anular_envios", return_value=False),
            patch("mpr.views.listar_tablero_por_articulo", return_value=[]) as m_par,
            patch("mpr.services.listar_tablero_pack", return_value=[]) as m_pack,
        ):
            response = view.get(request)
        return response, m_par, m_pack

    def test_default_es_par(self):
        response, m_par, m_pack = self._run()
        self.assertEqual(response.context_data["modo_tablero"], "par")
        m_par.assert_called_once()
        m_pack.assert_not_called()

    def test_modo_pack_usa_servicio_pack(self):
        response, m_par, m_pack = self._run({"modo": "pack"})
        self.assertEqual(response.context_data["modo_tablero"], "pack")
        m_pack.assert_called_once()
        m_par.assert_not_called()

    def test_modo_invalido_cae_en_par(self):
        response, m_par, m_pack = self._run({"modo": "otro"})
        self.assertEqual(response.context_data["modo_tablero"], "par")
        m_par.assert_called_once()
        m_pack.assert_not_called()
