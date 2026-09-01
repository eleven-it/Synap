"""Tests servicio/API relaciones Vendedor→Cliente→Sucursal→Marca."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.services.vendedor_cliente_marca import (
    ConflictoMarcaCliente,
    anular_terna,
    anular_ternas_lote,
    crear_terna,
    crear_ternas_lote,
    listar_ternas,
)
from ecom.vendedor_cliente_marca_views import (
    VendedorClienteMarcaAnularAPIView,
    VendedorClienteMarcaCrearAPIView,
    VendedorClienteMarcaTernasAPIView,
)


class _User:
    is_authenticated = True
    is_superuser = True

    def tiene_permiso(self, _codigo):
        return True


class TestCrearTernaConflicto(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca._domicilio_valido_cliente", return_value=(True, ""))
    @patch("ecom.services.vendedor_cliente_marca.buscar_dueno_marca_cliente")
    def test_conflicto_otro_viajante(self, mock_dueno, _dom):
        mock_dueno.return_value = {
            "id": 1,
            "CodViajante": 5,
            "id_cliente": 10,
            "id_cliente_domicilio": 3,
            "CodMarca": 2,
            "nombre_viajante": "Pérez",
        }
        with self.assertRaises(ConflictoMarcaCliente) as ctx:
            crear_terna("emp1", 9, 10, 2, 3, usuario_mod="test")
        self.assertEqual(ctx.exception.dueno["CodViajante"], 5)
        self.assertIn("Pérez", ctx.exception.message)
        mock_dueno.assert_called_once_with("emp1", 10, 2, 3)

    @patch("ecom.services.vendedor_cliente_marca._domicilio_valido_cliente", return_value=(True, ""))
    @patch("ecom.services.vendedor_cliente_marca.buscar_dueno_marca_cliente")
    def test_idempotente_mismo_viajante(self, mock_dueno, _dom):
        mock_dueno.return_value = {
            "id": 1,
            "CodViajante": 9,
            "id_cliente": 10,
            "id_cliente_domicilio": 3,
            "CodMarca": 2,
            "nombre_viajante": "Yo",
        }
        ok, msg, terna = crear_terna("emp1", 9, 10, 2, 3)
        self.assertTrue(ok)
        self.assertEqual(terna["CodViajante"], 9)
        self.assertEqual(terna["id_cliente_domicilio"], 3)

    @patch("ecom.services.vendedor_cliente_marca.buscar_dueno_marca_cliente")
    def test_rechaza_sin_sucursal(self, mock_dueno):
        mock_dueno.return_value = None
        ok, msg, terna = crear_terna("emp1", 9, 10, 2, 0)
        self.assertFalse(ok)
        self.assertIn("id_cliente_domicilio", msg.lower())
        self.assertIsNone(terna)


class TestCrearTernasLote(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca.crear_terna")
    def test_dos_ids_ambos_creados(self, mock_crear):
        mock_crear.side_effect = [
            (True, "Relación creada.", {"id": 1, "id_cliente_domicilio": 3}),
            (True, "Relación creada.", {"id": 2, "id_cliente_domicilio": 4}),
        ]
        res = crear_ternas_lote("emp1", 9, 10, 2, [3, 4])
        self.assertEqual(res["n_creadas"], 2)
        self.assertEqual(res["n_ya_existian"], 0)
        self.assertEqual(res["n_conflictos"], 0)
        self.assertEqual(len(res["creadas"]), 2)
        self.assertEqual(mock_crear.call_count, 2)

    @patch("ecom.services.vendedor_cliente_marca.crear_terna")
    def test_un_conflicto_un_creado(self, mock_crear):
        def side_effect(base, cv, ic, cm, idd, **kwargs):
            if idd == 3:
                raise ConflictoMarcaCliente(
                    "La marca ya está asignada a Pérez.",
                    {"CodViajante": 5, "nombre_viajante": "Pérez", "id": 1, "id_cliente_domicilio": 3},
                )
            return (True, "Relación creada.", {"id": 2, "id_cliente_domicilio": 4})

        mock_crear.side_effect = side_effect
        res = crear_ternas_lote("emp1", 9, 10, 2, [3, 4])
        self.assertEqual(res["n_creadas"], 1)
        self.assertEqual(res["n_conflictos"], 1)
        self.assertEqual(res["conflictos"][0]["id_cliente_domicilio"], 3)
        self.assertEqual(res["creadas"][0]["id_cliente_domicilio"], 4)

    @patch("ecom.services.vendedor_cliente_marca.crear_terna")
    def test_idempotente_mix(self, mock_crear):
        mock_crear.side_effect = [
            (True, "La relación ya existía.", {"id": 1, "id_cliente_domicilio": 3}),
            (True, "Relación creada.", {"id": 2, "id_cliente_domicilio": 4}),
        ]
        res = crear_ternas_lote("emp1", 9, 10, 2, [3, 4])
        self.assertEqual(res["n_creadas"], 1)
        self.assertEqual(res["n_ya_existian"], 1)
        self.assertEqual(res["n_conflictos"], 0)


class TestCrearTernasLoteMarcas(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca.crear_terna")
    def test_cartesiano_dos_marcas_dos_sucursales(self, mock_crear):
        mock_crear.side_effect = [
            (True, "Relación creada.", {"id": 1, "CodMarca": 2, "id_cliente_domicilio": 3}),
            (True, "Relación creada.", {"id": 2, "CodMarca": 2, "id_cliente_domicilio": 4}),
            (True, "Relación creada.", {"id": 3, "CodMarca": 7, "id_cliente_domicilio": 3}),
            (True, "Relación creada.", {"id": 4, "CodMarca": 7, "id_cliente_domicilio": 4}),
        ]
        res = crear_ternas_lote(
            "emp1", 9, 10, 2, [3, 4], cod_marcas=[2, 7]
        )
        self.assertEqual(res["n_creadas"], 4)
        self.assertEqual(mock_crear.call_count, 4)
        marcas_llamadas = [c.args[3] for c in mock_crear.call_args_list]
        sucs_llamadas = [c.args[4] for c in mock_crear.call_args_list]
        self.assertEqual(marcas_llamadas, [2, 2, 7, 7])
        self.assertEqual(sucs_llamadas, [3, 4, 3, 4])


class TestAnularTerna(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca.get_mysql_pool")
    def test_anular_ok(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.rowcount = 1
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        ok, msg = anular_terna("emp1", 3, usuario_mod="u")
        self.assertTrue(ok)
        self.assertIn("anulada", msg.lower())


class TestAnularTernasLote(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca.get_mysql_pool")
    def test_lote_anula_activas(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [(7,), (8,)]
        cursor.rowcount = 2
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = MagicMock(
            return_value=conn
        )
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(
            return_value=False
        )
        res = anular_ternas_lote("emp1", [7, 8, 9], usuario_mod="u")
        self.assertEqual(res["n_solicitadas"], 3)
        self.assertEqual(res["n_anuladas"], 2)
        self.assertEqual(res["n_omitidas"], 1)
        self.assertEqual(res["ids_anuladas"], [7, 8])


class TestListarTernas(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca.get_mysql_pool")
    def test_limite_predeterminado_y_tope_seguro(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        listar_ternas("emp1")
        self.assertEqual(cursor.execute.call_args.args[1][-1], 5000)

        listar_ternas("emp1", limit=50000)
        self.assertEqual(cursor.execute.call_args.args[1][-1], 20000)


class TestApiCrear409(TestCase):
    @patch("ecom.vendedor_cliente_marca_views.listar_ternas", return_value=(True, "", []))
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_ternas_usa_limite_predeterminado_del_servicio(self, _base, mock_listar):
        factory = APIRequestFactory()
        req = factory.get("/ecom/api/mayoristapp/vendedor-cliente-marca/ternas/?solo_activas=1")
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())

        resp = VendedorClienteMarcaTernasAPIView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_listar.call_args.kwargs["limit"], 5000)

    @patch("ecom.vendedor_cliente_marca_views.crear_terna")
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_post_conflicto_409(self, _base, mock_crear):
        mock_crear.side_effect = ConflictoMarcaCliente(
            "La marca ya está asignada a Pérez para este cliente y sucursal.",
            {"CodViajante": 5, "nombre_viajante": "Pérez", "id": 1, "id_cliente_domicilio": 3},
        )
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/crear/",
            {"CodViajante": 9, "id_cliente": 10, "CodMarca": 2, "id_cliente_domicilio": 3},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaCrearAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "conflicto_marca")
        self.assertEqual(resp.data["dueno"]["CodViajante"], 5)

    @patch("ecom.vendedor_cliente_marca_views.crear_ternas_lote")
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_post_lote_dos_ok_201(self, _base, mock_lote):
        mock_lote.return_value = {
            "creadas": [{"id": 1}, {"id": 2}],
            "ya_existian": [],
            "conflictos": [],
            "errores": [],
            "n_creadas": 2,
            "n_ya_existian": 0,
            "n_conflictos": 0,
            "n_errores": 0,
        }
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/crear/",
            {
                "CodViajante": 9,
                "id_cliente": 10,
                "CodMarca": 2,
                "ids_cliente_domicilio": [3, 4],
            },
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaCrearAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["ok"])
        self.assertTrue(resp.data["lote"])
        self.assertIn("2", resp.data["message"])

    @patch("ecom.vendedor_cliente_marca_views.crear_ternas_lote")
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_post_lote_todos_conflictos_409(self, _base, mock_lote):
        mock_lote.return_value = {
            "creadas": [],
            "ya_existian": [],
            "conflictos": [
                {"id_cliente_domicilio": 3, "error": "Conflicto", "dueno": {"CodViajante": 5}},
                {"id_cliente_domicilio": 4, "error": "Conflicto", "dueno": {"CodViajante": 5}},
            ],
            "errores": [],
            "n_creadas": 0,
            "n_ya_existian": 0,
            "n_conflictos": 2,
            "n_errores": 0,
        }
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/crear/",
            {
                "CodViajante": 9,
                "id_cliente": 10,
                "CodMarca": 2,
                "ids_cliente_domicilio": [3, 4],
            },
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaCrearAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "conflicto_marca")
        self.assertTrue(resp.data["lote"])
        self.assertEqual(resp.data["resumen"]["n_conflictos"], 2)

    @patch("ecom.vendedor_cliente_marca_views.crear_ternas_lote")
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_post_lote_marcas_y_sucursales_201(self, _base, mock_lote):
        mock_lote.return_value = {
            "creadas": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
            "ya_existian": [],
            "conflictos": [],
            "errores": [],
            "n_creadas": 4,
            "n_ya_existian": 0,
            "n_conflictos": 0,
            "n_errores": 0,
        }
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/crear/",
            {
                "CodViajante": 9,
                "id_cliente": 10,
                "CodMarcas": [2, 7],
                "ids_cliente_domicilio": [3, 4],
            },
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaCrearAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(mock_lote.call_args.kwargs["cod_marcas"], [2, 7])

    @patch("ecom.vendedor_cliente_marca_views.anular_terna", return_value=(True, "Relación anulada."))
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_anular_ok(self, _base, _anular):
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/anular/",
            {"id": 7},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaAnularAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])

    @patch("ecom.vendedor_cliente_marca_views.anular_ternas_lote")
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_anular_lote_ok(self, _base, mock_lote):
        mock_lote.return_value = {
            "n_solicitadas": 3,
            "n_anuladas": 3,
            "n_omitidas": 0,
            "ids_anuladas": [7, 8, 9],
        }
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/anular/",
            {"ids": [7, 8, 9]},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaAnularAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertTrue(resp.data["lote"])
        self.assertIn("3", resp.data["message"])
