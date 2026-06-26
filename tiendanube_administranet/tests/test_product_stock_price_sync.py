"""Tests — optimización sync productos (PATCH stock-price, sin GET)."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from tiendanube_administranet.services.sync_service import (
    STOCK_PRICE_BATCH_MAX,
    TiendanubeAdministraNETSyncService,
)
from tiendanube_administranet.services.tiendanube_service import TiendanubeService


class PatchProductsStockPriceTests(SimpleTestCase):
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    def test_patch_products_stock_price_ok(self, mock_request, _rate):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'id': 1, 'variants': [{'id': 10, 'success': True}]}]
        mock_request.return_value = mock_response

        config = MagicMock()
        config.store_id = '999'
        config.access_token = 'token'
        svc = TiendanubeService(config)
        items = [
            {
                'id': 1,
                'variants': [
                    {'id': 10, 'price': 99.5, 'inventory_levels': [{'stock': 3}]},
                ],
            }
        ]
        result = svc.patch_products_stock_price(items)

        self.assertTrue(result['success'])
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args
        self.assertEqual(call_kwargs[0][0], 'PATCH')
        self.assertIn('/products/stock-price', call_kwargs[0][1])
        self.assertEqual(call_kwargs[1]['json'], items)

    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    def test_patch_products_stock_price_error(self, mock_request, _rate):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = 'validation error'
        mock_request.return_value = mock_response

        config = MagicMock()
        config.store_id = '999'
        config.access_token = 'token'
        svc = TiendanubeService(config)
        result = svc.patch_products_stock_price([])

        self.assertFalse(result['success'])
        self.assertIn('422', result['message'])


class ProductSyncHelperTests(SimpleTestCase):
    def setUp(self):
        self.svc = TiendanubeAdministraNETSyncService.__new__(
            TiendanubeAdministraNETSyncService
        )

    def test_strip_images_from_create_payload(self):
        data = {'name': 'Artículo', 'images': [{'src': 'http://x/img.jpg'}], 'variants': []}
        stripped = self.svc._strip_images_from_product_payload(data)
        self.assertNotIn('images', stripped)
        self.assertEqual(stripped['name'], 'Artículo')

    def test_build_stock_price_patch_payload_agrupa_por_producto(self):
        pending = [
            {'product_id': 100, 'variant_id': 1, 'price': 10.0, 'stock': 5},
            {'product_id': 100, 'variant_id': 2, 'price': 20.0, 'stock': None},
            {'product_id': 200, 'variant_id': 3, 'price': None, 'stock': 7},
        ]
        payload = self.svc._build_stock_price_patch_payload(pending)
        self.assertEqual(len(payload), 2)
        p100 = next(p for p in payload if p['id'] == 100)
        self.assertEqual(len(p100['variants']), 2)
        self.assertEqual(p100['variants'][0]['inventory_levels'], [{'stock': 5}])

    def test_flush_stock_price_batch_llama_patch(self):
        mapping = MagicMock()
        adminet_product = {'IDArt': 42}
        pending = [{
            'product_id': 10,
            'variant_id': 20,
            'price': 15.0,
            'stock': 2,
            'mapping': mapping,
            'adminet_product': adminet_product,
        }]
        self.svc.product_service = MagicMock()
        self.svc.product_service.patch_products_stock_price.return_value = {
            'success': True,
        }
        self.svc.adminet_service = MagicMock()
        self.svc.adminet_service.update_product_tiendanube_id.return_value = {
            'success': True,
        }
        self.svc.adminet_config = MagicMock(deposito_tiendanube_id=2)
        self.svc.mapping_service = MagicMock()

        ok, fail = self.svc._flush_stock_price_batch(pending)

        self.assertEqual(ok, 1)
        self.assertEqual(fail, 0)
        self.assertEqual(len(pending), 0)
        self.svc.product_service.patch_products_stock_price.assert_called_once()

    def test_batch_max_constant(self):
        self.assertEqual(STOCK_PRICE_BATCH_MAX, 50)


class SyncProductsFromAdminetOptimizationTests(SimpleTestCase):
    def test_falla_sin_deposito_configurado(self):
        svc = TiendanubeAdministraNETSyncService.__new__(
            TiendanubeAdministraNETSyncService
        )
        svc.tiendanube_config = MagicMock()
        svc.adminet_config = MagicMock(deposito_tiendanube_id=None)
        sync_log = MagicMock()
        result = svc.sync_products_from_adminet(sync_log=sync_log)
        self.assertFalse(result['success'])
        self.assertIn('deposito_tiendanube_id', result['message'])
        sync_log.complete_sync.assert_called_once()

    @patch.object(TiendanubeAdministraNETSyncService, '_flush_stock_price_batch', return_value=(0, 0))
    @patch.object(TiendanubeAdministraNETSyncService, '_sync_product_create')
    @patch.object(TiendanubeAdministraNETSyncService, '_queue_stock_price_update', return_value=True)
    @patch.object(TiendanubeAdministraNETSyncService, '_get_product_variant_mapping')
    @patch.object(TiendanubeAdministraNETSyncService, '_sync_product_update_fallback')
    @patch('tiendanube_administranet.services.sync_service.ProductMapping')
    @patch('tiendanube_administranet.services.sync_service.SyncLog')
    def test_update_con_variant_id_no_llama_get(
        self,
        _sync_log_cls,
        mock_pm,
        mock_fallback,
        mock_get_variant,
        mock_queue,
        mock_create,
        _flush,
    ):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        svc.tiendanube_config = MagicMock()
        svc.adminet_config = MagicMock(deposito_tiendanube_id=2)
        svc.adminet_service = MagicMock()
        svc.adminet_service.get_products_with_stock_by_deposito.return_value = {
            'success': True,
            'results': [{'IDArt': 1, 'NombreArticulo': 'P1', 'stock_deposito': 5}],
        }
        svc.mapping_service = MagicMock()
        svc.mapping_service.map_adminet_to_tiendanube_product.return_value = {
            'variants': [{'price': 100, 'stock': 5, 'sku': 'SKU1'}],
        }
        svc.product_service = MagicMock()

        mapping = MagicMock()
        mapping.tiendanube_id = 555
        mapping.sync_status = 'pending'
        variant_mapping = MagicMock()
        variant_mapping.tiendanube_variant_id = 777
        mock_get_variant.return_value = variant_mapping
        mock_pm.objects.get_or_create.return_value = (mapping, False)

        sync_log = MagicMock()
        result = svc.sync_products_from_adminet(sync_log=sync_log)

        self.assertTrue(result['success'])
        mock_fallback.assert_not_called()
        mock_create.assert_not_called()
        svc.product_service.get_product.assert_not_called()
        mock_queue.assert_called_once()

    @patch.object(TiendanubeAdministraNETSyncService, '_flush_stock_price_batch', return_value=(0, 0))
    @patch.object(TiendanubeAdministraNETSyncService, '_sync_product_create')
    @patch.object(TiendanubeAdministraNETSyncService, '_get_product_variant_mapping', return_value=None)
    @patch.object(TiendanubeAdministraNETSyncService, '_sync_product_update_fallback')
    @patch.object(TiendanubeAdministraNETSyncService, '_finalize_product_sync_success')
    @patch('tiendanube_administranet.services.sync_service.ProductMapping')
    @patch('tiendanube_administranet.services.sync_service.SyncLog')
    def test_update_sin_variant_id_usa_fallback(
        self,
        _sync_log_cls,
        mock_pm,
        _finalize,
        mock_fallback,
        _get_variant,
        mock_create,
        _flush,
    ):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        svc.tiendanube_config = MagicMock()
        svc.adminet_config = MagicMock(deposito_tiendanube_id=2)
        svc.adminet_service = MagicMock()
        svc.adminet_service.get_products_with_stock_by_deposito.return_value = {
            'success': True,
            'results': [{'IDArt': 1, 'NombreArticulo': 'P1', 'stock_deposito': 5}],
        }
        svc.mapping_service = MagicMock()
        svc.mapping_service.map_adminet_to_tiendanube_product.return_value = {
            'variants': [{'price': 100, 'stock': 5}],
        }
        svc.product_service = MagicMock()

        mapping = MagicMock()
        mapping.tiendanube_id = 555
        mapping.sync_status = 'pending'
        mock_pm.objects.get_or_create.return_value = (mapping, False)
        mock_fallback.return_value = {'success': True}

        sync_log = MagicMock()
        svc.sync_products_from_adminet(sync_log=sync_log)

        mock_fallback.assert_called_once()
        mock_create.assert_not_called()

    @patch.object(TiendanubeAdministraNETSyncService, '_save_variant_mapping_from_tn_product')
    @patch.object(TiendanubeAdministraNETSyncService, '_finalize_product_sync_success')
    def test_sync_product_create_omite_imagenes_en_post(self, _finalize, _save_variant):
        svc = TiendanubeAdministraNETSyncService.__new__(
            TiendanubeAdministraNETSyncService
        )
        svc.product_service = MagicMock()
        svc.product_service.create_product.return_value = {
            'success': True,
            'product': {'id': 100, 'variants': [{'id': 200, 'sku': 'A'}]},
        }
        svc.adminet_service = MagicMock()
        mapping = MagicMock()
        tiendanube_data = {
            'name': 'Nuevo',
            'images': [{'src': 'http://img'}],
            'variants': [{'price': 1, 'stock': 1, 'sku': 'X'}],
        }
        svc._sync_product_create(mapping, tiendanube_data, {'IDArt': 9})

        payload = svc.product_service.create_product.call_args[0][0]
        self.assertNotIn('images', payload)
