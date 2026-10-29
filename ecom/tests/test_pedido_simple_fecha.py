"""La fecha de un pedido simple la determina el servidor, no el formulario."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from ecom.pedido_masivo_views import _resolver_cabecera_masivo


class PedidoSimpleFechaTests(SimpleTestCase):
    @patch("ecom.pedido_masivo_views._session_dias_no_laborables", return_value=[])
    @patch("ecom.pedido_masivo_views._flags_cabecera_masivo", return_value={
        "es_supervisor": False,
        "puede_editar_lista": False,
        "puede_editar_condicion": False,
    })
    @patch("ecom.pedido_masivo_views.parsear_cabecera_desde_body", return_value={
        "fecha_pedido": date(2000, 1, 1),
    })
    @patch("ecom.pedido_masivo_views.resolver_cabecera_comercial")
    def test_pedido_simple_ignora_fecha_enviada(self, resolver, _parsear, _flags, _dias):
        request = SimpleNamespace(session={})
        draft = SimpleNamespace(base_empresa="emp", id_cliente=7, modo="simple")

        _resolver_cabecera_masivo(request, draft, {})

        self.assertIsNone(resolver.call_args.kwargs["fecha_pedido"])

    @patch("ecom.pedido_masivo_views._session_dias_no_laborables", return_value=[])
    @patch("ecom.pedido_masivo_views._flags_cabecera_masivo", return_value={
        "es_supervisor": False,
        "puede_editar_lista": False,
        "puede_editar_condicion": False,
    })
    @patch("ecom.pedido_masivo_views.parsear_cabecera_desde_body", return_value={
        "fecha_pedido": date(2000, 1, 1),
    })
    @patch("ecom.pedido_masivo_views.resolver_cabecera_comercial")
    def test_pedido_masivo_conserva_fecha_permitida(self, resolver, _parsear, _flags, _dias):
        request = SimpleNamespace(session={})
        draft = SimpleNamespace(base_empresa="emp", id_cliente=7, modo="masivo")

        _resolver_cabecera_masivo(request, draft, {})

        self.assertEqual(resolver.call_args.kwargs["fecha_pedido"], date(2000, 1, 1))
