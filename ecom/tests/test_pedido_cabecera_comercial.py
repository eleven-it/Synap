"""Tests unitarios — cabecera comercial de pedidos e-commerce."""

from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase

from ecom.services.pedido_cabecera_comercial import (
    PedidoCabeceraComercial,
    calcular_vencimiento,
    puede_editar_cabecera_comercial,
    resolver_cabecera_comercial,
)


class TestCalcularVencimiento(TestCase):
    def test_fecha_mas_dias(self):
        fp = date(2026, 7, 10)
        self.assertEqual(calcular_vencimiento(fp, 15), date(2026, 7, 25))


class TestPermisosCabecera(TestCase):
    def test_supervisor_puede_editar(self):
        self.assertTrue(
            puede_editar_cabecera_comercial({"supervisor_venta": "Si"})
        )

    def test_vendedor_no_edita(self):
        self.assertFalse(
            puede_editar_cabecera_comercial({"supervisor_venta": "No", "id_vendedor_usr": 1})
        )


class TestResolverCabeceraComercial(TestCase):
    def _defaults(self):
        return {
            "id_cv": 4,
            "lista_id": 3,
            "cond_venta": "Cuenta Corriente",
            "dias_condicion": 20,
        }

    @patch("ecom.services.pedido_cabecera_comercial.cargar_defaults_cliente")
    @patch("ecom.services.pedido_cabecera_comercial._fetch_condicion")
    @patch("ecom.services.pedido_cabecera_comercial.dias_condicion")
    def test_vencimiento_auto(self, mock_dias, mock_fetch, mock_defaults):
        mock_defaults.return_value = self._defaults()
        mock_dias.return_value = 20
        mock_fetch.return_value = {"Descripcion": "Cuenta Corriente", "Dias": 20}
        cab, err = resolver_cabecera_comercial(
            "emp1",
            10,
            es_supervisor=False,
            fecha_pedido=date(2026, 7, 10),
            tipo_comprobante="PED",
        )
        self.assertIsNone(err)
        self.assertEqual(cab.vencimiento, date(2026, 7, 30))
        self.assertEqual(cab.lista_id, 3)
        self.assertEqual(cab.id_condventa, 4)

    @patch("ecom.services.pedido_cabecera_comercial.cargar_defaults_cliente")
    @patch("ecom.services.pedido_cabecera_comercial._fetch_condicion")
    @patch("ecom.services.pedido_cabecera_comercial.dias_condicion")
    def test_supervisor_cambia_lista_y_condicion(self, mock_dias, mock_fetch, mock_defaults):
        mock_defaults.return_value = self._defaults()
        mock_dias.side_effect = lambda _b, cv: 30 if cv == 7 else 20
        mock_fetch.side_effect = lambda _b, cod: {
            7: {"Descripcion": "30 días", "Dias": 30},
            4: {"Descripcion": "Cuenta Corriente", "Dias": 20},
        }.get(cod)

        cab, err = resolver_cabecera_comercial(
            "emp1",
            10,
            es_supervisor=True,
            fecha_pedido=date(2026, 7, 10),
            id_condventa=7,
            lista_id=5,
        )
        self.assertIsNone(err)
        self.assertEqual(cab.lista_id, 5)
        self.assertEqual(cab.id_condventa, 7)
        self.assertEqual(cab.vencimiento, date(2026, 8, 9))
        self.assertTrue(cab.editable_por_rol)

    @patch("ecom.services.pedido_cabecera_comercial.cargar_defaults_cliente")
    @patch("ecom.services.pedido_cabecera_comercial._fetch_condicion")
    @patch("ecom.services.pedido_cabecera_comercial.dias_condicion")
    def test_vendedor_ignora_override_lista(self, mock_dias, mock_fetch, mock_defaults):
        mock_defaults.return_value = self._defaults()
        mock_dias.return_value = 20
        mock_fetch.return_value = {"Descripcion": "Cuenta Corriente", "Dias": 20}
        cab, err = resolver_cabecera_comercial(
            "emp1",
            10,
            es_supervisor=False,
            lista_id=9,
            id_condventa=99,
        )
        self.assertIsNone(err)
        self.assertEqual(cab.lista_id, 3)
        self.assertEqual(cab.id_condventa, 4)

    @patch("ecom.services.pedido_cabecera_comercial.cargar_defaults_cliente")
    @patch("ecom.services.pedido_cabecera_comercial._fetch_condicion")
    @patch("ecom.services.pedido_cabecera_comercial.dias_condicion")
    def test_supervisor_override_vencimiento_valido(self, mock_dias, mock_fetch, mock_defaults):
        mock_defaults.return_value = self._defaults()
        mock_dias.return_value = 15
        mock_fetch.return_value = {"Descripcion": "Cuenta Corriente", "Dias": 15}
        ven = date(2026, 7, 20)
        cab, err = resolver_cabecera_comercial(
            "emp1",
            10,
            es_supervisor=True,
            fecha_pedido=date(2026, 7, 10),
            vencimiento=ven,
        )
        self.assertIsNone(err)
        self.assertEqual(cab.vencimiento, ven)

    @patch("ecom.services.pedido_cabecera_comercial.cargar_defaults_cliente")
    @patch("ecom.services.pedido_cabecera_comercial.dias_condicion")
    def test_override_vencimiento_anterior_rechazado(self, mock_dias, mock_defaults):
        mock_defaults.return_value = self._defaults()
        mock_dias.return_value = 15
        cab, err = resolver_cabecera_comercial(
            "emp1",
            10,
            es_supervisor=True,
            fecha_pedido=date(2026, 7, 10),
            vencimiento=date(2026, 7, 5),
        )
        self.assertIsNone(cab)
        self.assertIn("anterior", (err or "").lower())

    @patch("ecom.services.pedido_cabecera_comercial.cargar_defaults_cliente")
    @patch("ecom.services.pedido_cabecera_comercial._fetch_condicion")
    @patch("ecom.services.pedido_cabecera_comercial.dias_condicion")
    def test_recalculo_al_cambiar_fecha_pedido(self, mock_dias, mock_fetch, mock_defaults):
        mock_defaults.return_value = self._defaults()
        mock_dias.return_value = 7
        mock_fetch.return_value = {"Descripcion": "Cuenta Corriente", "Dias": 7}
        cab, _ = resolver_cabecera_comercial(
            "emp1",
            10,
            es_supervisor=False,
            fecha_pedido=date(2026, 8, 1),
        )
        self.assertEqual(cab.vencimiento, date(2026, 8, 8))
