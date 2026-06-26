"""Tests — detección de cambios para sync incremental."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import SimpleTestCase
from django.utils import timezone

from tiendanube_administranet.models import CustomerMapping, ProductMapping
from tiendanube_administranet.services.sync_change_detection import (
    adminet_fecha_modificado,
    cliente_adminet_cambio,
    cliente_tn_modificado,
    producto_requiere_sync_adminet_a_tn,
)


class AdminetFechaModificadoTests(SimpleTestCase):
    def test_sin_fecha_origen_no_dispara(self):
        self.assertFalse(adminet_fecha_modificado(None, timezone.now()))

    def test_sin_referencia_dispara(self):
        mod = timezone.now()
        self.assertTrue(adminet_fecha_modificado(mod, None))

    def test_fecha_posterior_dispara(self):
        ref = timezone.now() - timedelta(hours=1)
        mod = timezone.now()
        self.assertTrue(adminet_fecha_modificado(mod, ref))

    def test_fecha_igual_o_anterior_no_dispara(self):
        ref = timezone.now()
        self.assertFalse(adminet_fecha_modificado(ref, ref))
        self.assertFalse(
            adminet_fecha_modificado(ref - timedelta(minutes=5), ref)
        )


class ProductoRequiereSyncTests(SimpleTestCase):
    def _mapping_synced(self, **kwargs):
        m = MagicMock(spec=ProductMapping)
        m.sync_enabled = True
        m.sync_status = ProductMapping.SyncStatus.SYNCED
        m.sync_price = True
        m.sync_stock = True
        m.tiendanube_id = 100
        m.adminet_fecha_mod = timezone.now() - timedelta(days=1)
        m.adminet_stock = 10
        m.tiendanube_price = Decimal('100.00')
        m.tiendanube_cost = Decimal('50.00')
        for k, v in kwargs.items():
            setattr(m, k, v)
        return m

    def test_synced_sin_cambios_omite(self):
        ahora = timezone.now()
        mapping = self._mapping_synced(
            adminet_fecha_mod=ahora,
            adminet_stock=10,
            tiendanube_price=Decimal('121.00'),
            tiendanube_cost=Decimal('60.50'),
        )
        articulo = {
            'fecha_mod': ahora,
            'stock_deposito': 10,
            'Precio4V': 100,
            'Precio4VI': 121,
            'PrecioCosto': 50,
        }
        necesita, motivo = producto_requiere_sync_adminet_a_tn(
            mapping, articulo, deposito_id=3
        )
        self.assertFalse(necesita)
        self.assertEqual(motivo, 'sin cambios')

    def test_fecha_mod_posterior_dispara(self):
        mapping = self._mapping_synced()
        articulo = {
            'fecha_mod': timezone.now(),
            'stock_deposito': 10,
            'Precio4V': 100,
            'Precio4VI': 121,
            'PrecioCosto': 50,
        }
        necesita, motivo = producto_requiere_sync_adminet_a_tn(
            mapping, articulo, deposito_id=3
        )
        self.assertTrue(necesita)
        self.assertIn('fecha_mod', motivo)

    def test_stock_distinto_dispara(self):
        ahora = timezone.now()
        mapping = self._mapping_synced(adminet_fecha_mod=ahora, adminet_stock=5)
        articulo = {
            'fecha_mod': ahora,
            'stock_deposito': 12,
            'saldo': 20,
            'saldo_pedido_cliente': 8,
            'Precio4V': 100,
            'Precio4VI': 121,
            'PrecioCosto': 50,
        }
        necesita, motivo = producto_requiere_sync_adminet_a_tn(
            mapping, articulo, deposito_id=3
        )
        self.assertTrue(necesita)
        self.assertIn('stock', motivo)

    def test_precio_distinto_dispara(self):
        ahora = timezone.now()
        mapping = self._mapping_synced(
            adminet_fecha_mod=ahora,
            tiendanube_price=Decimal('100.00'),
        )
        articulo = {
            'fecha_mod': ahora,
            'stock_deposito': 10,
            'Precio4V': 150,
            'Precio4VI': 181.5,
            'PrecioCosto': 50,
        }
        necesita, motivo = producto_requiere_sync_adminet_a_tn(
            mapping, articulo, deposito_id=3
        )
        self.assertTrue(necesita)
        self.assertIn('precio', motivo)

    def test_force_siempre_dispara(self):
        mapping = self._mapping_synced()
        articulo = {'fecha_mod': mapping.adminet_fecha_mod, 'stock_deposito': 10}
        necesita, _ = producto_requiere_sync_adminet_a_tn(
            mapping, articulo, deposito_id=3, force=True
        )
        self.assertTrue(necesita)


class ClienteCambioTests(SimpleTestCase):
    def _mapping_cliente(self, **kwargs):
        m = MagicMock(spec=CustomerMapping)
        m.sync_status = CustomerMapping.SyncStatus.SYNCED
        m.adminet_nombre = 'Juan Pérez'
        m.adminet_email = 'juan@ejemplo.com'
        m.adminet_cuit = '20123456789'
        m.adminet_telefono = '1111'
        m.adminet_calle = 'Calle Falsa'
        m.adminet_nro_calle = '123'
        m.adminet_cliente_ecommerce = 'Si'
        m.tiendanube_id = 999
        m.tiendanube_updated_at = timezone.now() - timedelta(days=1)
        for k, v in kwargs.items():
            setattr(m, k, v)
        return m

    def test_cliente_adminet_sin_cambios(self):
        mapping = self._mapping_cliente()
        customer = {
            'nombre_cliente': 'Juan Pérez',
            'Email': 'juan@ejemplo.com',
            'CUIT': '20123456789',
            'telefono': '1111',
            'Calle': 'Calle Falsa',
            'NroCalle': '123',
            'cliente_ecommerce': 'Si',
            'id_tiendanube': 999,
        }
        self.assertFalse(cliente_adminet_cambio(mapping, customer))

    def test_cliente_adminet_email_cambiado(self):
        mapping = self._mapping_cliente()
        customer = {
            'nombre_cliente': 'Juan Pérez',
            'Email': 'nuevo@ejemplo.com',
            'CUIT': '20123456789',
            'telefono': '1111',
            'Calle': 'Calle Falsa',
            'NroCalle': '123',
            'cliente_ecommerce': 'Si',
        }
        self.assertTrue(cliente_adminet_cambio(mapping, customer))

    def test_cliente_tn_updated_at_posterior(self):
        mapping = self._mapping_cliente()
        tn_customer = {
            'updated_at': (timezone.now() + timedelta(hours=1)).isoformat(),
        }
        self.assertTrue(cliente_tn_modificado(tn_customer, mapping))

    def test_cliente_tn_sin_cambios(self):
        updated = timezone.now() - timedelta(hours=2)
        mapping = self._mapping_cliente(tiendanube_updated_at=updated)
        tn_customer = {'updated_at': updated.isoformat()}
        self.assertFalse(cliente_tn_modificado(tn_customer, mapping))
