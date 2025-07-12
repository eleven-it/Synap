from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
from mercadopago.models import MercadoPagoConfig, MercadoPagoDevice, MercadoPagoTransaction
from mercadopago.services.payment_service import MercadoPagoPaymentService
from mercadopago.services.smartpos_service import MercadoPagoSmartPOSService, MercadoPagoDeviceManager
from core.models import Empresa, Branch, UsuarioExtendido


class MercadoPagoPaymentServiceTest(TestCase):
    """Tests para el servicio de pagos"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Company",
            cuit="12345678901"
        )
        self.branch = Branch.objects.create(
            nombre="Test Branch",
            empresa=self.empresa
        )
        self.config = MercadoPagoConfig.objects.create(
            empresa=self.empresa,
            client_id="test_client_id",
            client_secret="test_client_secret",
            is_active=True
        )
        self.device = MercadoPagoDevice.objects.create(
            name="Test Device",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            status="active",
            supported_payment_methods=["credit_card", "debit_card"]
        )
    
    @patch('mercadopago.services.api_client.MercadoPagoAPIClient')
    def test_create_payment_preference(self, mock_api_client):
        """Test crear preferencia de pago"""
        # Mock de la respuesta de la API
        mock_response = {
            'id': 'test_preference_id',
            'init_point': 'https://www.mercadopago.com/checkout/v1/redirect?pref_id=test_preference_id',
            'sandbox_init_point': 'https://sandbox.mercadopago.com/checkout/v1/redirect?pref_id=test_preference_id'
        }
        mock_api_client.return_value.create_preference.return_value = mock_response
        
        service = MercadoPagoPaymentService(self.empresa)
        result = service.create_payment_preference(
            amount=Decimal('100.50'),
            description="Test payment"
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['preference_id'], 'test_preference_id')
        
        # Verificar que se creó la transacción
        transaction = MercadoPagoTransaction.objects.filter(
            external_reference=result['external_reference']
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('100.50'))
    
    @patch('mercadopago.services.api_client.MercadoPagoAPIClient')
    def test_process_smartpos_payment(self, mock_api_client):
        """Test procesar pago en SmartPOS"""
        # Mock de la respuesta de la API
        mock_response = {
            'id': 'test_payment_id',
            'status': 'approved',
            'status_detail': 'accredited'
        }
        mock_api_client.return_value.process_smartpos_payment.return_value = mock_response
        
        service = MercadoPagoPaymentService(self.empresa)
        result = service.process_smartpos_payment(
            amount=Decimal('100.50'),
            payment_method="credit_card",
            branch=self.branch
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'approved')
        
        # Verificar que se creó la transacción
        transaction = MercadoPagoTransaction.objects.filter(
            external_reference=result['external_reference']
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.device, self.device)
    
    @patch('mercadopago.services.api_client.MercadoPagoAPIClient')
    def test_get_payment_status(self, mock_api_client):
        """Test obtener estado de pago"""
        # Mock de la respuesta de la API
        mock_response = {
            'id': 'test_payment_id',
            'status': 'approved',
            'status_detail': 'accredited'
        }
        mock_api_client.return_value.get_payment.return_value = mock_response
        
        # Crear transacción
        transaction = MercadoPagoTransaction.objects.create(
            external_reference="test_ref_123",
            mercadopago_id="test_payment_id",
            empresa=self.empresa,
            amount=Decimal('100'),
            payment_method="credit_card",
            payment_type="smartpos",
            status="pending"
        )
        
        service = MercadoPagoPaymentService(self.empresa)
        result = service.get_payment_status("test_payment_id")
        
        self.assertEqual(result['status'], 'approved')
        
        # Verificar que se actualizó la transacción
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'approved')
    
    def test_get_transactions(self):
        """Test obtener transacciones filtradas"""
        # Crear transacciones de prueba
        MercadoPagoTransaction.objects.create(
            external_reference="test_ref_1",
            mercadopago_id="test_mp_1",
            empresa=self.empresa,
            branch=self.branch,
            amount=Decimal('100'),
            payment_method="credit_card",
            payment_type="smartpos",
            status="approved"
        )
        MercadoPagoTransaction.objects.create(
            external_reference="test_ref_2",
            mercadopago_id="test_mp_2",
            empresa=self.empresa,
            branch=self.branch,
            amount=Decimal('200'),
            payment_method="debit_card",
            payment_type="smartpos",
            status="pending"
        )
        
        service = MercadoPagoPaymentService(self.empresa)
        
        # Test sin filtros
        transactions = service.get_transactions()
        self.assertEqual(len(transactions), 2)
        
        # Test con filtro de estado
        approved_transactions = service.get_transactions(status="approved")
        self.assertEqual(len(approved_transactions), 1)
        self.assertEqual(approved_transactions[0].status, "approved")
        
        # Test con filtro de sucursal
        branch_transactions = service.get_transactions(branch=self.branch)
        self.assertEqual(len(branch_transactions), 2)


class MercadoPagoSmartPOSServiceTest(TestCase):
    """Tests para el servicio de SmartPOS"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Company",
            cuit="12345678901"
        )
        self.branch = Branch.objects.create(
            nombre="Test Branch",
            empresa=self.empresa
        )
        self.config = MercadoPagoConfig.objects.create(
            empresa=self.empresa,
            client_id="test_client_id",
            client_secret="test_client_secret",
            is_active=True
        )
        self.device = MercadoPagoDevice.objects.create(
            name="Test Device",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            status="active",
            supported_payment_methods=["credit_card", "debit_card"]
        )
    
    @patch('mercadopago.services.api_client.MercadoPagoAPIClient')
    def test_register_device(self, mock_api_client):
        """Test registrar dispositivo"""
        # Mock de la respuesta de la API
        mock_response = {
            'id': 'test_device_id',
            'status': 'active'
        }
        mock_api_client.return_value.register_smartpos_device.return_value = mock_response
        
        service = MercadoPagoSmartPOSService(self.device)
        result = service.register_device()
        
        self.assertNotIn('error', result)
        
        # Verificar que se actualizó el dispositivo
        self.device.refresh_from_db()
        self.assertEqual(self.device.device_id, 'test_device_id')
        self.assertEqual(self.device.status, 'active')
    
    @patch('mercadopago.services.api_client.MercadoPagoAPIClient')
    def test_sync_device_status(self, mock_api_client):
        """Test sincronizar estado del dispositivo"""
        # Configurar device_id
        self.device.device_id = "test_device_id"
        self.device.save()
        
        # Mock de la respuesta de la API
        mock_response = {
            'status': 'active',
            'connection_status': 'connected'
        }
        mock_api_client.return_value.get_smartpos_device_status.return_value = mock_response
        
        service = MercadoPagoSmartPOSService(self.device)
        result = service.sync_device_status()
        
        self.assertNotIn('error', result)
        
        # Verificar que se actualizó el estado
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, 'active')
        self.assertEqual(self.device.connection_status, 'connected')
    
    @patch('mercadopago.services.api_client.MercadoPagoAPIClient')
    def test_process_payment(self, mock_api_client):
        """Test procesar pago en dispositivo"""
        # Configurar device_id
        self.device.device_id = "test_device_id"
        self.device.save()
        
        # Mock de la respuesta de la API
        mock_response = {
            'id': 'test_payment_id',
            'status': 'approved',
            'status_detail': 'accredited'
        }
        mock_api_client.return_value.process_smartpos_payment.return_value = mock_response
        
        service = MercadoPagoSmartPOSService(self.device)
        result = service.process_payment(
            amount=100.50,
            payment_method="credit_card"
        )
        
        self.assertNotIn('error', result)
        self.assertEqual(result['status'], 'approved')
        
        # Verificar que se actualizó last_transaction
        self.device.refresh_from_db()
        self.assertIsNotNone(self.device.last_transaction)


class MercadoPagoDeviceManagerTest(TestCase):
    """Tests para el gestor de dispositivos"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Company",
            cuit="12345678901"
        )
        self.branch = Branch.objects.create(
            nombre="Test Branch",
            empresa=self.empresa
        )
        self.config = MercadoPagoConfig.objects.create(
            empresa=self.empresa,
            client_id="test_client_id",
            client_secret="test_client_secret",
            is_active=True
        )
    
    def test_get_all_devices(self):
        """Test obtener todos los dispositivos"""
        # Crear dispositivos de prueba
        MercadoPagoDevice.objects.create(
            name="Device 1",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            status="active"
        )
        MercadoPagoDevice.objects.create(
            name="Device 2",
            device_type="mobile_pos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            status="inactive"
        )
        
        manager = MercadoPagoDeviceManager(self.empresa)
        
        # Test sin filtros
        devices = manager.get_all_devices()
        self.assertEqual(len(devices), 2)
        
        # Test con filtro de estado
        active_devices = manager.get_all_devices(status="active")
        self.assertEqual(len(active_devices), 1)
        self.assertEqual(active_devices[0].status, "active")
        
        # Test con filtro de sucursal
        branch_devices = manager.get_all_devices(branch=self.branch)
        self.assertEqual(len(branch_devices), 2)
    
    def test_get_device_summary(self):
        """Test obtener resumen de dispositivos"""
        # Crear dispositivos de prueba
        MercadoPagoDevice.objects.create(
            name="Device 1",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            status="active",
            connection_status="connected"
        )
        MercadoPagoDevice.objects.create(
            name="Device 2",
            device_type="mobile_pos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            status="inactive",
            connection_status="disconnected"
        )
        
        manager = MercadoPagoDeviceManager(self.empresa)
        summary = manager.get_device_summary()
        
        self.assertEqual(summary['total_devices'], 2)
        self.assertEqual(summary['active_devices'], 1)
        self.assertEqual(summary['connected_devices'], 1)
        
        # Verificar resumen por estado
        status_summary = {item['status']: item['count'] for item in summary['status_summary']}
        self.assertEqual(status_summary['active'], 1)
        self.assertEqual(status_summary['inactive'], 1) 