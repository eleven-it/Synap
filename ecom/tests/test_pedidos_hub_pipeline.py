"""Tests pipeline hub Lista|Kanban."""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from ecom.models import EcomCart, EcomCartItem, EcomPedidoMasivoDraft
from ecom.services.pedidos_hub_pipeline import (
    _columna_ped_mysql,
    archivar_borrador_masivo,
    construir_hub_pedidos,
)


class TestColumnaPed(TestCase):
    def test_clasificacion(self):
        self.assertEqual(_columna_ped_mysql("Si", "No Autorizado", "Pendiente"), "anulado")
        self.assertEqual(_columna_ped_mysql("No", "No Autorizado", "Pendiente"), "por_autorizar")
        self.assertEqual(_columna_ped_mysql("No", "Autorizado", "Pendiente"), "enviado")
        self.assertEqual(_columna_ped_mysql("No", "Autorizado", "En preparación"), "aprobado")


class TestConstruirHub(TestCase):
    @patch("ecom.services.pedidos_hub_pipeline._pedidos_mysql", return_value=[])
    def test_incluye_borradores(self, _mysql):
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
        self.assertTrue(any(i.get("badge_error") for i in borr["items"]))
        self.assertEqual(hub["borradores_activos"], borr["count"])

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
