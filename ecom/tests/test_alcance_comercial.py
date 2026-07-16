# Tests alcance comercial (REQ-JER-04, REQ-GLOB-01): OFF=[cv], ON por rol.

import unittest
from unittest.mock import patch

from ecom.services.alcance_comercial import alcance_viajantes_comercial


class TestAlcanceOff(unittest.TestCase):
    @patch("ecom.services.alcance_comercial.workflow_jerarquia_comercial_activo", return_value=False)
    def test_off_vendedor_solo_propio(self, _wf):
        ctx = {"id_vendedor_usr": 42}
        self.assertEqual(alcance_viajantes_comercial("emp1", ctx), [42])

    @patch("ecom.services.alcance_comercial.workflow_jerarquia_comercial_activo", return_value=False)
    def test_off_supervisor_cartera_legacy(self, _wf):
        ctx = {"id_vendedor_usr": 10, "vendedor_a_cargo": [20, 21]}
        self.assertEqual(alcance_viajantes_comercial("emp1", ctx), [10, 20, 21])

    @patch("ecom.services.alcance_comercial.workflow_jerarquia_comercial_activo", return_value=False)
    def test_cache_request(self, _wf):
        ctx = {"id_vendedor_usr": 5}
        r1 = alcance_viajantes_comercial("emp1", ctx)
        ctx["id_vendedor_usr"] = 99
        r2 = alcance_viajantes_comercial("emp1", ctx)
        self.assertEqual(r1, r2)
        self.assertEqual(r1, [5])


class TestAlcanceOn(unittest.TestCase):
    @patch("ecom.services.alcance_comercial.puede_ver_todos_pedidos", return_value=False)
    @patch("ecom.services.alcance_comercial.subarbol_de", return_value=[10, 20, 21])
    @patch("ecom.services.alcance_comercial.rol_de", return_value="supervisor")
    @patch("ecom.services.alcance_comercial.workflow_jerarquia_comercial_activo", return_value=True)
    def test_on_supervisor_subarbol(self, _wf, _rol, mock_sub, _vt):
        ctx = {"id_vendedor_usr": 10}
        self.assertEqual(alcance_viajantes_comercial("emp1", ctx), [10, 20, 21])
        mock_sub.assert_called_once_with("emp1", 10, "supervisor")

    @patch("ecom.services.alcance_comercial._listar_todos_viajantes", return_value=[1, 2, 3])
    @patch("ecom.services.alcance_comercial.puede_ver_todos_pedidos", return_value=True)
    @patch("ecom.services.alcance_comercial.workflow_jerarquia_comercial_activo", return_value=True)
    def test_on_ver_todos(self, _wf, _vt, mock_todos):
        ctx = {"id_vendedor_usr": 10, "synap_permisos": ["ecom.pedidos.ver_todos"]}
        self.assertEqual(alcance_viajantes_comercial("emp1", ctx), [1, 2, 3])
        mock_todos.assert_called_once_with("emp1")

    @patch("ecom.services.alcance_comercial.subarbol_de", return_value=[99])
    @patch("ecom.services.alcance_comercial.rol_de", return_value="vendedor")
    @patch("ecom.services.alcance_comercial.puede_ver_todos_pedidos", return_value=False)
    @patch("ecom.services.alcance_comercial.workflow_jerarquia_comercial_activo", return_value=True)
    def test_on_vendedor_propio(self, _wf, _vt, _rol, _sub):
        ctx = {"id_vendedor_usr": 99}
        self.assertEqual(alcance_viajantes_comercial("emp1", ctx), [99])
