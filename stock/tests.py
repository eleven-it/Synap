# Tests del módulo Stock (AdministraNET).
from django.test import TestCase
from django.urls import reverse


class StockURLTests(TestCase):
    """Comprueba que las URLs del módulo stock resuelven (vistas requieren login/permiso)."""

    def test_alta_movimiento_url_resolves(self):
        url = reverse("stock:alta_movimiento")
        self.assertEqual(url, "/stock/ingreso-movimiento/")

    def test_visualiza_movimientos_url_resolves(self):
        url = reverse("stock:visualiza_movimientos")
        self.assertEqual(url, "/stock/movimientos/")

    def test_ref_movstock_list_url_resolves(self):
        url = reverse("stock:ref_movstock_list")
        self.assertEqual(url, "/stock/referencias/")

    def test_inventario_url_resolves(self):
        url = reverse("stock:inventario")
        self.assertEqual(url, "/stock/inventario/")

    def test_movimiento_pdf_url_resolves(self):
        url = reverse("stock:movimiento_pdf", kwargs={"codigo_movimiento": 1})
        self.assertEqual(url, "/stock/movimientos/1/pdf/")
