"""Tests de inferencia cliente BEST → AdministraNET."""

from django.test import SimpleTestCase

from mpr.best_migration.client_matcher import match_clients


def _admin(codigo: int, nombre: str, cuit: str = "", fantasia: str = "") -> dict:
    return {
        "Codigo": codigo,
        "nombre_cliente": nombre,
        "nombre_fantasia": fantasia,
        "CUIT": cuit,
        "id_manual_cli": "",
    }


class ClientMatcherTokenCompartidoTest(SimpleTestCase):
    """Coincidencia por token significativo y fuzzy ortográfico."""

    def test_jose_geronimo_vs_geronimo_deportes(self):
        admin = [_admin(949, "GERONIMO Deportes")]
        best = [{"best_cliente": "JOSE GERONIMO", "best_cuit": "", "ordenes_abiertas": 1}]
        results = match_clients(best_rows=best, admin_clients=admin)
        self.assertEqual(len(results), 1)
        m = results[0]
        self.assertIn(m.status, ("AMBIGUO", "INFERIDO"))
        self.assertGreaterEqual(m.score or 0, 55)
        self.assertEqual(m.admin_codigo, 949)
        self.assertIn("GERONIMO", m.razon)

    def test_dulio_del_greco_vs_grecco(self):
        admin = [_admin(100, "DULIO DEL GRECCO E HIJOS S.R.L")]
        best = [{"best_cliente": "DULIO DEL GRECO", "best_cuit": "", "ordenes_abiertas": 2}]
        results = match_clients(best_rows=best, admin_clients=admin)
        self.assertEqual(len(results), 1)
        m = results[0]
        self.assertIn(m.status, ("AMBIGUO", "INFERIDO"))
        self.assertGreaterEqual(m.score or 0, 55)
        self.assertEqual(m.admin_codigo, 100)
        self.assertTrue(
            "GRECO" in m.razon or "tokens_compartidos" in m.razon,
            msg=f"razon inesperada: {m.razon}",
        )

    def test_sin_overlap_queda_sin_candidato(self):
        admin = [_admin(1, "ACME INDUSTRIAS SA"), _admin(2, "BETA COMERCIAL")]
        best = [{"best_cliente": "OMEGA ZZZQ", "best_cuit": "", "ordenes_abiertas": 1}]
        results = match_clients(best_rows=best, admin_clients=admin)
        self.assertEqual(results[0].status, "SIN_CANDIDATO")
        self.assertIsNone(results[0].admin_codigo)

    def test_cuit_exacto_sigue_siendo_100(self):
        admin = [_admin(500, "CLIENTE CUALQUIERA", cuit="30-71234567-8")]
        best = [
            {
                "best_cliente": "NOMBRE DISTINTO",
                "best_cuit": "30712345678",
                "ordenes_abiertas": 1,
            }
        ]
        results = match_clients(best_rows=best, admin_clients=admin)
        m = results[0]
        self.assertEqual(m.status, "INFERIDO")
        self.assertEqual(m.score, 100)
        self.assertEqual(m.razon, "cuit_exacto")
        self.assertEqual(m.admin_codigo, 500)
