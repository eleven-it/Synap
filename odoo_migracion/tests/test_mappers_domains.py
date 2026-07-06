"""Tests mappers y dominios."""

from django.test import SimpleTestCase

from odoo_migracion.mappers import map_cliente, map_marca, map_rubro
from odoo_migracion.services.change_detection import row_payload_hash
from odoo_migracion.services.domains import DOMAIN_BY_KEY, ordered_domain_keys
from odoo_migracion.services.external_id import ref_adminet


class MapperTests(SimpleTestCase):
    def test_map_rubro(self):
        aid, vals = map_rubro({"CodigoRubro": 5, "NombreRubro": "Electrónica"})
        self.assertEqual(aid, "5")
        self.assertEqual(vals["name"], "Electrónica")
        self.assertEqual(vals["ref"], ref_adminet("rubro", 5))

    def test_map_marca_active(self):
        aid, vals = map_marca({"CodMarca": 1, "NombreMarca": "Samsung", "anulado": "No"})
        self.assertTrue(vals["active"])
        self.assertEqual(vals["code"], "1")

    def test_map_cliente_customer_rank(self):
        aid, vals = map_cliente({"Codigo": 100, "nombre_cliente": "ACME", "CUIT": "30-12345678-9"})
        self.assertEqual(vals["customer_rank"], 1)
        self.assertIn("30123456789", vals["vat"])


class DomainRegistryTests(SimpleTestCase):
    def test_ordered_includes_viajante_before_cliente(self):
        keys = ordered_domain_keys()
        self.assertLess(keys.index("viajante"), keys.index("cliente"))

    def test_all_domains_have_mapper(self):
        for key, spec in DOMAIN_BY_KEY.items():
            self.assertTrue(callable(spec.mapper), key)


class ChangeDetectionTests(SimpleTestCase):
    def test_hash_stable(self):
        row = {"a": 1, "b": "x"}
        self.assertEqual(row_payload_hash(row), row_payload_hash({"b": "x", "a": 1}))
