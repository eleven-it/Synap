"""Vista web lista presupuestos vendedor."""
from django.test import Client, SimpleTestCase


class PresupuestosVendedorWebTests(SimpleTestCase):
    def test_sin_sesion_redirige_login(self):
        c = Client(HTTP_HOST="127.0.0.1")
        resp = c.get("/ecom/mayoristapp/presupuestos-vendedor/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.headers.get("Location", ""))
