"""Tests contratos API 2026 — visibility XOR published, inventory_levels."""

from django.test import SimpleTestCase, TestCase

from tiendanube_administranet.models import TiendanubeConfig
from tiendanube_administranet.services.sync_service import (
    TiendanubeAdministraNETSyncService,
    build_inventory_level_entry,
    normalize_product_visibility_payload,
)


class NormalizeProductVisibilityPayloadTests(SimpleTestCase):
    def test_convierte_published_a_visibility_sin_ambos(self):
        payload = normalize_product_visibility_payload({
            'name': 'Artículo',
            'published': True,
        })

        self.assertEqual(payload['visibility'], 'visible')
        self.assertNotIn('published', payload)

    def test_published_false_usa_hidden(self):
        payload = normalize_product_visibility_payload({
            'name': 'Oculto',
            'published': False,
        })

        self.assertEqual(payload['visibility'], 'hidden')
        self.assertNotIn('published', payload)

    def test_visibility_existente_elimina_published(self):
        payload = normalize_product_visibility_payload({
            'name': 'Con visibility',
            'visibility': 'visible',
            'published': True,
        })

        self.assertEqual(payload['visibility'], 'visible')
        self.assertNotIn('published', payload)


class BuildInventoryLevelEntryTests(SimpleTestCase):
    def test_sin_location_id_solo_stock(self):
        entry = build_inventory_level_entry(12)

        self.assertEqual(entry, {'stock': 12})
        self.assertNotIn('location_id', entry)

    def test_con_location_id_incluye_campo(self):
        entry = build_inventory_level_entry(7, location_id=987654)

        self.assertEqual(entry, {'stock': 7, 'location_id': 987654})


class BuildStockPricePatchPayloadTests(SimpleTestCase):
    def setUp(self):
        self.svc = TiendanubeAdministraNETSyncService.__new__(
            TiendanubeAdministraNETSyncService
        )

    def test_payload_stock_sin_location_id(self):
        pending = [
            {'product_id': 100, 'variant_id': 1, 'price': None, 'stock': 5},
        ]
        payload = self.svc._build_stock_price_patch_payload(pending, location_id=None)

        levels = payload[0]['variants'][0]['inventory_levels']
        self.assertEqual(levels, [{'stock': 5}])

    def test_payload_stock_con_location_id(self):
        pending = [
            {'product_id': 200, 'variant_id': 2, 'price': 10.0, 'stock': 3},
        ]
        payload = self.svc._build_stock_price_patch_payload(
            pending, location_id=555001,
        )

        levels = payload[0]['variants'][0]['inventory_levels']
        self.assertEqual(
            levels,
            [{'stock': 3, 'location_id': 555001}],
        )


class TiendanubeConfigLocationIdTests(TestCase):
    def test_location_id_opcional_vacio_por_defecto(self):
        config = TiendanubeConfig.objects.create(
            name='Tienda sin location',
            store_id='loc-empty-1',
            access_token='token',
        )

        self.assertIsNone(config.location_id)

    def test_location_id_persiste_valor(self):
        config = TiendanubeConfig.objects.create(
            name='Tienda con location',
            store_id='loc-set-1',
            access_token='token',
            location_id=424242,
        )

        config.refresh_from_db()
        self.assertEqual(config.location_id, 424242)
