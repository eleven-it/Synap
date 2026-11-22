from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.cliente_relay_views import ClienteTransporteAPIView
from ecom.services.cliente_transporte import fijar_transporte_cliente


class TestClienteTransporte(TestCase):
    def setUp(self):
        contexto = patch("ecom.cliente_relay_views._session_user", side_effect=lambda req: req.session["user"])
        contexto.start()
        self.addCleanup(contexto.stop)

    def _request(self, tipo="vendedor"):
        request = APIRequestFactory().post(
            "/ecom/api/mayoristapp/clientes/transporte/",
            {"codigo": 904, "id_domicilio": 10, "id_transporte": 4}, format="json",
        )
        request.session = {"user": {"base_empresa": "bestsox", "id_usuario": 2, "tipousuario": tipo}}
        user = MagicMock(is_authenticated=True, is_superuser=False)
        force_authenticate(request, user=user)
        return request

    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=False)
    @patch("ecom.cliente_relay_views.fijar_transporte_cliente")
    def test_no_modifica_cliente_fuera_de_cartera(self, guardar, _acceso):
        response = ClienteTransporteAPIView.as_view()(self._request())
        self.assertEqual(response.status_code, 403)
        guardar.assert_not_called()

    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.cliente_relay_views.fijar_transporte_cliente", return_value=True)
    @patch("ecom.cliente_relay_views.consultar_transportes_cliente", return_value={"transportes": [], "domicilios": []})
    def test_guarda_transporte_en_domicilio(self, _listar, guardar, _acceso):
        response = ClienteTransporteAPIView.as_view()(self._request())
        self.assertEqual(response.status_code, 200)
        guardar.assert_called_once_with("bestsox", 904, 10, 4)

    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=True)
    @patch("ecom.cliente_relay_views.fijar_transporte_cliente")
    def test_cliente_no_modifica_transporte(self, guardar, _acceso):
        response = ClienteTransporteAPIView.as_view()(self._request(tipo="cliente"))
        self.assertEqual(response.status_code, 403)
        guardar.assert_not_called()

    @patch("ecom.services.cliente_transporte.get_mysql_pool")
    def test_servicio_valida_transporte_y_domicilio_activos(self, pool):
        conn = pool.return_value.get_connection.return_value.__enter__.return_value
        cursor = conn.cursor.return_value
        cursor.fetchone.return_value = (1,)
        cursor.rowcount = 1
        self.assertTrue(fijar_transporte_cliente("bestsox", 904, 10, 4))
        self.assertIn("anulado = 'No'", cursor.execute.call_args_list[1].args[0])
        self.assertEqual(cursor.execute.call_args_list[1].args[1], [4, 10, 904])
        conn.commit.assert_called_once()
