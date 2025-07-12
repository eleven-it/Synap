from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from mercadopago.models import MercadoPagoConfig, MercadoPagoDevice, MercadoPagoTransaction
from core.models import Empresa, Branch, UsuarioExtendido


class MercadoPagoConfigModelTest(TestCase):
    """Tests para el modelo MercadoPagoConfig"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Company",
            cuit="12345678901"
        )
        self.user = UsuarioExtendido.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_create_config(self):
        """Test crear configuración básica"""
        config = MercadoPagoConfig.objects.create(
            empresa=self.empresa,
            client_id="test_client_id",
            client_secret="test_client_secret",
            created_by=self.user
        )
        
        self.assertEqual(config.empresa, self.empresa)
        self.assertTrue(config.is_active)
        self.assertTrue(config.is_sandbox)
        self.assertEqual(config.commission_percentage, Decimal('0'))
    
    def test_config_validation(self):
        """Test validaciones del modelo"""
        # Commission percentage > 100
        with self.assertRaises(ValidationError):
            config = MercadoPagoConfig(
                empresa=self.empresa,
                client_id="test",
                client_secret="test",
                commission_percentage=Decimal('150')
            )
            config.full_clean()
        
        # Max installments > 60
        with self.assertRaises(ValidationError):
            config = MercadoPagoConfig(
                empresa=self.empresa,
                client_id="test",
                client_secret="test",
                max_installments=100
            )
            config.full_clean()
    
    def test_config_methods(self):
        """Test métodos del modelo"""
        config = MercadoPagoConfig.objects.create(
            empresa=self.empresa,
            client_id="test",
            client_secret="test"
        )
        
        # Test API URLs
        self.assertIn("sandbox", config.get_api_base_url())
        self.assertIn("point", config.get_smartpos_api_url())
        
        # Test webhook URLs
        self.assertIn("webhook", config.get_webhook_url())
        self.assertIn("smartpos-webhook", config.get_smartpos_webhook_url())


class MercadoPagoDeviceModelTest(TestCase):
    """Tests para el modelo MercadoPagoDevice"""
    
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
            client_id="test",
            client_secret="test"
        )
        self.user = UsuarioExtendido.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_create_device(self):
        """Test crear dispositivo básico"""
        device = MercadoPagoDevice.objects.create(
            name="Test Device",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            created_by=self.user
        )
        
        self.assertEqual(device.name, "Test Device")
        self.assertEqual(device.device_type, "smartpos")
        self.assertEqual(device.status, "inactive")
        self.assertTrue(device.is_active)
    
    def test_device_default_validation(self):
        """Test validación de dispositivo default"""
        # Crear primer dispositivo default
        device1 = MercadoPagoDevice.objects.create(
            name="Device 1",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            is_default=True
        )
        
        # Crear segundo dispositivo default (debería desactivar el primero)
        device2 = MercadoPagoDevice.objects.create(
            name="Device 2",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            is_default=True
        )
        
        # Verificar que el primer dispositivo ya no es default
        device1.refresh_from_db()
        self.assertFalse(device1.is_default)
        self.assertTrue(device2.is_default)
    
    def test_device_methods(self):
        """Test métodos del dispositivo"""
        device = MercadoPagoDevice.objects.create(
            name="Test Device",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config,
            supported_payment_methods=["credit_card", "debit_card"]
        )
        
        # Test can_process_payment
        self.assertTrue(device.can_process_payment(Decimal('100'), "credit_card"))
        self.assertFalse(device.can_process_payment(Decimal('100'), "cash"))
        
        # Test update_status
        device.update_status("active", "connected")
        self.assertEqual(device.status, "active")
        self.assertEqual(device.connection_status, "connected")


class MercadoPagoTransactionModelTest(TestCase):
    """Tests para el modelo MercadoPagoTransaction"""
    
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
            client_id="test",
            client_secret="test"
        )
        self.device = MercadoPagoDevice.objects.create(
            name="Test Device",
            device_type="smartpos",
            empresa=self.empresa,
            branch=self.branch,
            config=self.config
        )
    
    def test_create_transaction(self):
        """Test crear transacción básica"""
        transaction = MercadoPagoTransaction.objects.create(
            external_reference="test_ref_123",
            mercadopago_id="test_mp_123",
            empresa=self.empresa,
            branch=self.branch,
            device=self.device,
            amount=Decimal('100.50'),
            payment_method="credit_card",
            payment_type="smartpos",
            status="pending"
        )
        
        self.assertEqual(transaction.amount, Decimal('100.50'))
        self.assertEqual(transaction.status, "pending")
        self.assertEqual(transaction.currency, "ARS")
    
    def test_transaction_validation(self):
        """Test validaciones de transacción"""
        # Amount <= 0
        with self.assertRaises(ValidationError):
            transaction = MercadoPagoTransaction(
                external_reference="test_ref",
                mercadopago_id="test_mp",
                empresa=self.empresa,
                amount=Decimal('0')
            )
            transaction.full_clean()
        
        # Installments < 1
        with self.assertRaises(ValidationError):
            transaction = MercadoPagoTransaction(
                external_reference="test_ref",
                mercadopago_id="test_mp",
                empresa=self.empresa,
                amount=Decimal('100'),
                installments=0
            )
            transaction.full_clean()
    
    def test_transaction_methods(self):
        """Test métodos de transacción"""
        transaction = MercadoPagoTransaction.objects.create(
            external_reference="test_ref_123",
            mercadopago_id="test_mp_123",
            empresa=self.empresa,
            amount=Decimal('100'),
            payment_method="credit_card",
            payment_type="smartpos",
            status="approved"
        )
        
        # Test can_be_refunded
        self.assertTrue(transaction.can_be_refunded())
        
        # Test get_status_display_color
        color = transaction.get_status_display_color()
        self.assertIn(color, ['green', 'red', 'yellow', 'gray'])
        
        # Test commission calculation
        commission = transaction.get_commission_amount()
        self.assertEqual(commission, Decimal('0'))
    
    def test_transaction_save_processed_at(self):
        """Test que processed_at se actualiza automáticamente"""
        transaction = MercadoPagoTransaction.objects.create(
            external_reference="test_ref_123",
            mercadopago_id="test_mp_123",
            empresa=self.empresa,
            amount=Decimal('100'),
            payment_method="credit_card",
            payment_type="smartpos",
            status="pending"
        )
        
        # Inicialmente processed_at debe ser None
        self.assertIsNone(transaction.processed_at)
        
        # Cambiar status a approved
        transaction.status = "approved"
        transaction.save()
        
        # Ahora processed_at debe tener un valor
        self.assertIsNotNone(transaction.processed_at) 