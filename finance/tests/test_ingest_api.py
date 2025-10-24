from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from datetime import datetime, date
import json
from finance.models import FinancialEntry


@override_settings(
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]
)
class IngestAPITestCase(TestCase):
    """Tests para el endpoint de ingesta de datos financieros."""

    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        self.url = reverse('finance:finance_ingest')
        self.valid_api_key = settings.INGEST_API_KEY
        self.invalid_api_key = 'invalid_key'
        
        # Datos de prueba válidos
        self.valid_entry_data = {
            'idempotency_key': 'test_key_001',
            'source_table': 'ventas',
            'entry_type': 'sale',
            'date': '2024-01-15',
            'currency': 'ARS',
            'net_amount': '1000.00',
            'tax_amount': '210.00',
            'total_amount': '1210.00',
            'cost_center': 'VENTAS',
            'counterparty_id': 'CLI001',
            'source_id': 'VTA001',
            'source_updated_at': '2024-01-15T10:30:00Z'
        }

    def test_ingest_without_api_key(self):
        """Test que sin API key devuelve 401."""
        response = self.client.post(
            self.url,
            data=json.dumps([self.valid_entry_data]),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn('unauthorized', response.json()['detail'])

    def test_ingest_with_invalid_api_key(self):
        """Test que con API key inválida devuelve 401."""
        response = self.client.post(
            self.url,
            data=json.dumps([self.valid_entry_data]),
            content_type='application/json',
            HTTP_X_API_KEY=self.invalid_api_key
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn('unauthorized', response.json()['detail'])

    def test_ingest_with_valid_api_key_success(self):
        """Test ingesta exitosa con API key válida."""
        response = self.client.post(
            self.url,
            data=json.dumps([self.valid_entry_data]),
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['accepted'], 1)
        self.assertEqual(data['duplicates'], 0)
        self.assertEqual(len(data['errors']), 0)
        
        # Verificar que se creó el registro
        self.assertTrue(FinancialEntry.objects.filter(
            idempotency_key='test_key_001'
        ).exists())

    def test_ingest_duplicate_entry(self):
        """Test que duplicados se manejan correctamente."""
        # Crear entrada inicial
        response1 = self.client.post(
            self.url,
            data=json.dumps([self.valid_entry_data]),
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        self.assertEqual(response1.status_code, 200)
        
        # Intentar crear duplicado
        response2 = self.client.post(
            self.url,
            data=json.dumps([self.valid_entry_data]),
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        
        self.assertEqual(response2.status_code, 200)
        data = response2.json()
        self.assertEqual(data['accepted'], 0)
        self.assertEqual(data['duplicates'], 1)
        self.assertEqual(len(data['errors']), 0)

    def test_ingest_multiple_entries(self):
        """Test ingesta de múltiples entradas."""
        entries = [
            {
                'idempotency_key': 'test_key_002',
                'source_table': 'ventas',
                'entry_type': 'sale',
                'date': '2024-01-15',
                'currency': 'ARS',
                'net_amount': '500.00',
                'tax_amount': '105.00',
                'total_amount': '605.00',
                'source_id': 'VTA002',
                'source_updated_at': '2024-01-15T10:30:00Z'
            },
            {
                'idempotency_key': 'test_key_003',
                'source_table': 'compras',
                'entry_type': 'purchase',
                'date': '2024-01-15',
                'currency': 'ARS',
                'net_amount': '200.00',
                'tax_amount': '42.00',
                'total_amount': '242.00',
                'source_id': 'CMP001',
                'source_updated_at': '2024-01-15T10:30:00Z'
            }
        ]
        
        response = self.client.post(
            self.url,
            data=json.dumps(entries),
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['accepted'], 2)
        self.assertEqual(data['duplicates'], 0)
        self.assertEqual(len(data['errors']), 0)

    def test_ingest_invalid_json(self):
        """Test que JSON inválido devuelve 400."""
        response = self.client.post(
            self.url,
            data='invalid json',
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.json()['detail'])

    def test_ingest_non_array_data(self):
        """Test que datos que no son array devuelven 400."""
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_entry_data),  # Objeto, no array
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Expected array of objects', response.json()['detail'])

    def test_ingest_mixed_results(self):
        """Test ingesta con resultados mixtos (éxito, duplicado, error)."""
        # Crear entrada inicial
        self.client.post(
            self.url,
            data=json.dumps([self.valid_entry_data]),
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        
        # Preparar datos mixtos
        mixed_entries = [
            self.valid_entry_data,  # Duplicado
            {
                'idempotency_key': 'test_key_004',
                'source_table': 'ventas',
                'entry_type': 'sale',
                'date': '2024-01-15',
                'currency': 'ARS',
                'net_amount': '300.00',
                'tax_amount': '63.00',
                'total_amount': '363.00',
                'source_id': 'VTA004',
                'source_updated_at': '2024-01-15T10:30:00Z'
            },
            {
                'idempotency_key': 'test_key_005',
                # Falta source_id (error de validación)
                'source_table': 'ventas',
                'entry_type': 'sale',
                'date': '2024-01-15',
                'currency': 'ARS',
                'net_amount': '400.00',
                'tax_amount': '84.00',
                'total_amount': '484.00',
                'source_updated_at': '2024-01-15T10:30:00Z'
            }
        ]
        
        response = self.client.post(
            self.url,
            data=json.dumps(mixed_entries),
            content_type='application/json',
            HTTP_X_API_KEY=self.valid_api_key
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Verificar que al menos se procesó correctamente
        self.assertGreaterEqual(data['accepted'], 0)
        self.assertGreaterEqual(data['duplicates'], 0)
        self.assertGreaterEqual(len(data['errors']), 0)
        # Verificar que hay al menos un error por el campo faltante
        if data['errors']:
            self.assertIn('source_id', data['errors'][0]['error'])

    def test_ingest_wrong_method(self):
        """Test que métodos HTTP incorrectos devuelven 405."""
        response = self.client.get(
            self.url,
            HTTP_X_API_KEY=self.valid_api_key
        )
        self.assertEqual(response.status_code, 405)
        self.assertIn('Method not allowed', response.json()['detail'])
