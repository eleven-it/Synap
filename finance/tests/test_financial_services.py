from django.test import TestCase, override_settings
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime
from finance.models import FinancialEntry
from finance.services import (
    get_monthly_financial_summary,
    get_annual_financial_summary,
    get_financial_summary_by_period
)


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
class FinancialServicesTestCase(TestCase):
    """Tests para las funciones de servicios financieros."""

    def setUp(self):
        """Configuración inicial para los tests."""
        # Crear datos de prueba para diferentes meses y tipos
        test_data = [
            # Enero 2024 - Ventas
            {
                'idempotency_key': 'test_sale_jan_001',
                'source_table': 'ventas',
                'entry_type': 'sale',
                'date': date(2024, 1, 15),
                'currency': 'ARS',
                'net_amount': Decimal('1000.00'),
                'tax_amount': Decimal('210.00'),
                'total_amount': Decimal('1210.00'),
                'source_id': 'VTA001',
                'source_updated_at': timezone.make_aware(datetime(2024, 1, 15, 10, 30))
            },
            {
                'idempotency_key': 'test_sale_jan_002',
                'source_table': 'ventas',
                'entry_type': 'sale',
                'date': date(2024, 1, 20),
                'currency': 'ARS',
                'net_amount': Decimal('500.00'),
                'tax_amount': Decimal('105.00'),
                'total_amount': Decimal('605.00'),
                'source_id': 'VTA002',
                'source_updated_at': timezone.make_aware(datetime(2024, 1, 20, 10, 30))
            },
            # Enero 2024 - Compras
            {
                'idempotency_key': 'test_purchase_jan_001',
                'source_table': 'compras',
                'entry_type': 'purchase',
                'date': date(2024, 1, 10),
                'currency': 'ARS',
                'net_amount': Decimal('300.00'),
                'tax_amount': Decimal('63.00'),
                'total_amount': Decimal('363.00'),
                'source_id': 'CMP001',
                'source_updated_at': timezone.make_aware(datetime(2024, 1, 10, 10, 30))
            },
            # Febrero 2024 - Ventas
            {
                'idempotency_key': 'test_sale_feb_001',
                'source_table': 'ventas',
                'entry_type': 'sale',
                'date': date(2024, 2, 5),
                'currency': 'ARS',
                'net_amount': Decimal('800.00'),
                'tax_amount': Decimal('168.00'),
                'total_amount': Decimal('968.00'),
                'source_id': 'VTA003',
                'source_updated_at': timezone.make_aware(datetime(2024, 2, 5, 10, 30))
            },
            # Febrero 2024 - Compras
            {
                'idempotency_key': 'test_purchase_feb_001',
                'source_table': 'compras',
                'entry_type': 'purchase',
                'date': date(2024, 2, 12),
                'currency': 'ARS',
                'net_amount': Decimal('200.00'),
                'tax_amount': Decimal('42.00'),
                'total_amount': Decimal('242.00'),
                'source_id': 'CMP002',
                'source_updated_at': timezone.make_aware(datetime(2024, 2, 12, 10, 30))
            },
            # Diferente moneda (USD)
            {
                'idempotency_key': 'test_sale_usd_001',
                'source_table': 'ventas',
                'entry_type': 'sale',
                'date': date(2024, 1, 25),
                'currency': 'USD',
                'net_amount': Decimal('100.00'),
                'tax_amount': Decimal('21.00'),
                'total_amount': Decimal('121.00'),
                'source_id': 'VTA004',
                'source_updated_at': timezone.make_aware(datetime(2024, 1, 25, 10, 30))
            }
        ]
        
        # Crear registros en la base de datos
        for data in test_data:
            FinancialEntry.objects.create(**data)

    def test_get_monthly_financial_summary_ars(self):
        """Test resumen mensual para moneda ARS."""
        result = get_monthly_financial_summary(2024, 'ARS')
        
        # Debe tener 2 meses (enero y febrero)
        self.assertEqual(len(result), 2)
        
        # Verificar enero
        jan_data = next(item for item in result if item['month'] == '2024-01')
        self.assertEqual(jan_data['income'], Decimal('1500.00'))  # 1000 + 500
        self.assertEqual(jan_data['cost'], Decimal('300.00'))
        self.assertEqual(jan_data['margin'], Decimal('1200.00'))  # 1500 - 300
        
        # Verificar febrero
        feb_data = next(item for item in result if item['month'] == '2024-02')
        self.assertEqual(feb_data['income'], Decimal('800.00'))
        self.assertEqual(feb_data['cost'], Decimal('200.00'))
        self.assertEqual(feb_data['margin'], Decimal('600.00'))  # 800 - 200

    def test_get_monthly_financial_summary_usd(self):
        """Test resumen mensual para moneda USD."""
        result = get_monthly_financial_summary(2024, 'USD')
        
        # Debe tener 1 mes (enero)
        self.assertEqual(len(result), 1)
        
        # Verificar enero USD
        jan_data = next(item for item in result if item['month'] == '2024-01')
        self.assertEqual(jan_data['income'], Decimal('100.00'))
        self.assertEqual(jan_data['cost'], Decimal('0.00'))
        self.assertEqual(jan_data['margin'], Decimal('100.00'))

    def test_get_monthly_financial_summary_no_data(self):
        """Test resumen mensual para año sin datos."""
        result = get_monthly_financial_summary(2023, 'ARS')
        self.assertEqual(len(result), 0)

    def test_get_monthly_financial_summary_invalid_year(self):
        """Test validación de año inválido."""
        with self.assertRaises(ValueError):
            get_monthly_financial_summary(99, 'ARS')
        
        with self.assertRaises(ValueError):
            get_monthly_financial_summary(10000, 'ARS')
        
        with self.assertRaises(ValueError):
            get_monthly_financial_summary('invalid', 'ARS')

    def test_get_annual_financial_summary_ars(self):
        """Test resumen anual para moneda ARS."""
        result = get_annual_financial_summary(2024, 'ARS')
        
        self.assertEqual(result['year'], 2024)
        self.assertEqual(result['currency'], 'ARS')
        self.assertEqual(result['income'], Decimal('2300.00'))  # 1500 + 800
        self.assertEqual(result['cost'], Decimal('500.00'))  # 300 + 200
        self.assertEqual(result['margin'], Decimal('1800.00'))  # 2300 - 500
        self.assertEqual(result['transaction_count'], 5)  # 5 transacciones ARS

    def test_get_annual_financial_summary_usd(self):
        """Test resumen anual para moneda USD."""
        result = get_annual_financial_summary(2024, 'USD')
        
        self.assertEqual(result['year'], 2024)
        self.assertEqual(result['currency'], 'USD')
        self.assertEqual(result['income'], Decimal('100.00'))
        self.assertEqual(result['cost'], Decimal('0.00'))
        self.assertEqual(result['margin'], Decimal('100.00'))
        self.assertEqual(result['transaction_count'], 1)

    def test_get_annual_financial_summary_no_data(self):
        """Test resumen anual para año sin datos."""
        result = get_annual_financial_summary(2023, 'ARS')
        
        self.assertEqual(result['year'], 2023)
        self.assertEqual(result['currency'], 'ARS')
        self.assertEqual(result['income'], Decimal('0.00'))
        self.assertEqual(result['cost'], Decimal('0.00'))
        self.assertEqual(result['margin'], Decimal('0.00'))
        self.assertEqual(result['transaction_count'], 0)

    def test_get_financial_summary_by_period(self):
        """Test resumen por período de años."""
        result = get_financial_summary_by_period(2024, 2024, 'ARS')
        
        self.assertEqual(result['period'], '2024-2024')
        self.assertEqual(result['currency'], 'ARS')
        self.assertEqual(result['income'], Decimal('2300.00'))
        self.assertEqual(result['cost'], Decimal('500.00'))
        self.assertEqual(result['margin'], Decimal('1800.00'))
        self.assertEqual(result['transaction_count'], 5)
        self.assertEqual(result['years'], [2024])

    def test_get_financial_summary_by_period_invalid_range(self):
        """Test validación de rango de años inválido."""
        with self.assertRaises(ValueError):
            get_financial_summary_by_period(2025, 2024, 'ARS')  # start > end

    def test_get_financial_summary_by_period_invalid_years(self):
        """Test validación de años inválidos."""
        with self.assertRaises(ValueError):
            get_financial_summary_by_period(99, 2024, 'ARS')
        
        with self.assertRaises(ValueError):
            get_financial_summary_by_period(2024, 10000, 'ARS')


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
class MonthlyReportAPITestCase(TestCase):
    """Tests para el endpoint de reporte mensual."""

    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = TestCase.client_class()
        self.url = '/finance/api/finance/monthly-report'

    def test_monthly_report_get_success(self):
        """Test petición GET exitosa."""
        response = self.client.get(self.url, {'year': '2024', 'currency': 'ARS'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('year', data)
        self.assertIn('currency', data)
        self.assertIn('monthly', data)
        self.assertIn('annual', data)
        self.assertEqual(data['year'], 2024)
        self.assertEqual(data['currency'], 'ARS')

    def test_monthly_report_post_success(self):
        """Test petición POST exitosa."""
        import json
        response = self.client.post(
            self.url,
            data=json.dumps({'year': 2024, 'currency': 'ARS'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('year', data)
        self.assertIn('currency', data)
        self.assertIn('monthly', data)
        self.assertIn('annual', data)

    def test_monthly_report_missing_year(self):
        """Test error cuando falta el parámetro year."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('missing year', data['detail'])

    def test_monthly_report_invalid_year(self):
        """Test error con año inválido."""
        response = self.client.get(self.url, {'year': 'invalid'})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('year must be a valid integer', data['detail'])

    def test_monthly_report_year_out_of_range(self):
        """Test error con año fuera de rango."""
        response = self.client.get(self.url, {'year': '99'})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('year must be a 4-digit integer', data['detail'])

    def test_monthly_report_default_currency(self):
        """Test que la moneda por defecto es ARS."""
        response = self.client.get(self.url, {'year': '2024'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['currency'], 'ARS')
