# -*- coding: utf-8 -*-
"""Alcance comercial en objetivos CRUD (REQ-OBJ-01)."""

import unittest
from unittest.mock import MagicMock, patch

from ventas.services.objetivos_mysql import (
    agrupar_grupos_arbol_org,
    alcance_objetivos_cod_viajante,
    ctx_desde_session_user,
    usar_vista_arbol_org,
    _sql_filtro_alcance_cv,
)


class TestCtxObjetivos(unittest.TestCase):
    def test_ctx_desde_session_user(self):
        ctx = ctx_desde_session_user({"id_vendedor_usr": 42, "base_empresa": "emp1"})
        self.assertEqual(ctx["id_vendedor_usr"], 42)
        self.assertEqual(ctx["base_empresa"], "emp1")


class TestAlcanceObjetivos(unittest.TestCase):
    @patch("ecom.services.alcance_comercial.alcance_viajantes_comercial", return_value=[42])
    def test_alcance_con_ctx(self, mock_alc):
        ctx = {"id_vendedor_usr": 42}
        self.assertEqual(alcance_objetivos_cod_viajante("emp1", ctx), [42])
        mock_alc.assert_called_once_with("emp1", ctx)

    def test_alcance_sin_ctx_sin_filtro(self):
        self.assertIsNone(alcance_objetivos_cod_viajante("emp1", None))

    def test_sql_filtro_vacio(self):
        sql, params = _sql_filtro_alcance_cv([])
        self.assertIn("1=0", sql.replace(" ", ""))
        self.assertEqual(params, [])

    def test_sql_filtro_in(self):
        sql, params = _sql_filtro_alcance_cv([10, 20])
        self.assertIn("IN", sql)
        self.assertEqual(params, [10, 20])


class TestVistaArbolOrg(unittest.TestCase):
    @patch("ecom.services.jerarquia_comercial.rol_de", return_value="gerente")
    @patch("ecom.services.ecom_config_mysql.workflow_jerarquia_comercial_activo", return_value=True)
    @patch("ecom.services.pedido_permisos.puede_ver_todos_pedidos", return_value=False)
    def test_gerente_usa_arbol(self, _vt, _wf, _rol):
        self.assertTrue(usar_vista_arbol_org("emp1", {"id_vendedor_usr": 1}))

    @patch("ecom.services.ecom_config_mysql.workflow_jerarquia_comercial_activo", return_value=False)
    def test_off_sin_arbol(self, _wf):
        self.assertFalse(usar_vista_arbol_org("emp1", {"id_vendedor_usr": 1}))


class TestAgruparArbolOrg(unittest.TestCase):
    @patch("ventas.services.objetivos_mysql.usar_vista_arbol_org", return_value=False)
    def test_off_devuelve_grupos_planos(self, _u):
        grupos = [{"cod_viajante": 20, "nombre_vendedor": "V20", "clientes": []}]
        self.assertEqual(agrupar_grupos_arbol_org("emp1", {"id_vendedor_usr": 1}, grupos), grupos)

    @patch("ventas.services.objetivos_mysql._nombres_viajantes_map", return_value={10: "S10", 20: "V20", 1: "G1"})
    @patch("ventas.services.objetivos_mysql._relaciones_org_activas", return_value=({20: [10]}, {10: 1}))
    @patch("ventas.services.objetivos_mysql.usar_vista_arbol_org", return_value=True)
    def test_on_anida_gerente_supervisor_vendedor(self, _u, _rel, _nom):
        grupos = [{"cod_viajante": 20, "nombre_vendedor": "V20", "clientes": [{"codigo": 1}]}]
        arbol = agrupar_grupos_arbol_org("emp1", {"id_vendedor_usr": 1}, grupos)
        self.assertEqual(len(arbol), 1)
        self.assertEqual(arbol[0]["tipo"], "gerente")
        self.assertEqual(arbol[0]["children"][0]["tipo"], "supervisor")
        self.assertEqual(arbol[0]["children"][0]["children"][0]["tipo"], "vendedor")

    @patch("ventas.services.objetivos_mysql._nombres_viajantes_map", return_value={10: "S10", 11: "S11", 20: "V20"})
    @patch("ventas.services.objetivos_mysql._relaciones_org_activas", return_value=({20: [10, 11]}, {}))
    @patch("ventas.services.objetivos_mysql.usar_vista_arbol_org", return_value=True)
    def test_on_repite_vendedor_bajo_cada_supervisor(self, _u, _rel, _nom):
        grupos = [{"cod_viajante": 20, "nombre_vendedor": "V20", "clientes": [{"codigo": 1}]}]

        arbol = agrupar_grupos_arbol_org("emp1", {"id_vendedor_usr": 1}, grupos)

        self.assertEqual({nodo["cod_viajante"] for nodo in arbol}, {10, 11})
        self.assertTrue(all(nodo["children"][0]["cod_viajante"] == 20 for nodo in arbol))


class TestListarGruposAlcance(unittest.TestCase):
    @patch("ventas.services.objetivos_mysql.get_mysql_pool")
    @patch("ventas.services.objetivos_mysql.alcance_objetivos_cod_viajante", return_value=[10, 20])
    def test_listar_aplica_filtro_in(self, mock_alc, mock_pool_fn):
        from ventas.services.objetivos_mysql import listar_grupos_objetivos

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,)]
        cursor.fetchall.return_value = []
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        ok, err, rows = listar_grupos_objetivos("emp1", 1, ctx={"id_vendedor_usr": 10})
        self.assertTrue(ok)
        self.assertEqual(rows, [])
        sql = cursor.execute.call_args[0][0]
        self.assertIn("CodViajante IN", sql)
        self.assertEqual(cursor.execute.call_args[0][1], [1, 10, 20])
