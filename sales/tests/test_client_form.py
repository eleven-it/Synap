from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from sales.models import Client
from sales.forms import ClientForm
from core.models import Empresa, Branch

User = get_user_model()


class ClientFormTestCase(TestCase):
    """Tests para el formulario de clientes"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre="Test Company",
            identificador_fiscal="12345678"
        )
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Test Branch"
        )
        
        # Crear usuario
        self.user = User.objects.create_user(
            email="test@example.com",
            nombre="Test User"
        )
        
        # Crear cliente de prueba
        self.client_obj = Client.objects.create(
            name="Test Client",
            code="TEST001",
            email="client@example.com",
            phone="123456789",
            is_active=True
        )
    
    def test_client_form_valid_data(self):
        """Test que el formulario acepta datos válidos"""
        form_data = {
            'name': 'New Test Client',
            'code': 'NEW001',
            'tax_id': '12345678901',
            'address': '123 Test Street',
            'city': 'Test City',
            'state': 'Test State',
            'postal_code': '12345',
            'country': 'Argentina',
            'contact_person': 'John Doe',
            'email': 'newclient@example.com',
            'phone': '987654321',
            'mobile': '555123456',
            'website': 'https://www.testclient.com',
            'notes': 'Test notes',
            'is_active': True
        }
        
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_client_form_invalid_email(self):
        """Test que el formulario rechaza emails inválidos"""
        form_data = {
            'name': 'Test Client',
            'email': 'invalid-email',
            'phone': '123456789'
        }
        
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_client_form_missing_contact_methods(self):
        """Test que el formulario requiere al menos un método de contacto"""
        form_data = {
            'name': 'Test Client',
            # Sin email, phone o mobile
        }
        
        form = ClientForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
    
    def test_client_form_with_phone_only(self):
        """Test que el formulario es válido con solo teléfono"""
        form_data = {
            'name': 'Test Client',
            'phone': '123456789'
        }
        
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_client_form_with_email_only(self):
        """Test que el formulario es válido con solo email"""
        form_data = {
            'name': 'Test Client',
            'email': 'test@example.com'
        }
        
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_client_form_with_mobile_only(self):
        """Test que el formulario es válido con solo móvil"""
        form_data = {
            'name': 'Test Client',
            'mobile': '555123456'
        }
        
        form = ClientForm(data=form_data)
        self.assertTrue(form.is_valid())


class ClientViewsTestCase(TestCase):
    """Tests para las vistas de clientes"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre="Test Company",
            identificador_fiscal="12345678"
        )
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Test Branch"
        )
        
        # Crear usuario
        self.user = User.objects.create_user(
            email="test@example.com",
            nombre="Test User"
        )
        
        # Crear cliente de prueba
        self.client_obj = Client.objects.create(
            name="Test Client",
            code="TEST001",
            email="client@example.com",
            phone="123456789",
            is_active=True
        )
        
        # Configurar cliente HTTP
        self.client = Client()
    
    def test_client_create_view_get(self):
        """Test que la vista de creación de clientes responde correctamente"""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        # Hacer request GET
        response = self.client.get(reverse('sales:client_create'))
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_form.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], ClientForm)
    
    def test_client_create_view_post_valid(self):
        """Test que la vista de creación acepta datos válidos"""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        # Datos válidos
        form_data = {
            'name': 'New Test Client',
            'code': 'NEW001',
            'email': 'newclient@example.com',
            'phone': '123456789',
            'is_active': True
        }
        
        # Hacer request POST
        response = self.client.post(reverse('sales:client_create'), form_data)
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el cliente fue creado
        self.assertTrue(Client.objects.filter(name='New Test Client').exists())
    
    def test_client_create_view_post_invalid(self):
        """Test que la vista de creación maneja datos inválidos"""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        # Datos inválidos (sin métodos de contacto)
        form_data = {
            'name': 'Invalid Client',
            # Sin email, phone o mobile
        }
        
        # Hacer request POST
        response = self.client.post(reverse('sales:client_create'), form_data)
        
        # Verificar que se muestra el formulario con errores
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
    
    def test_client_update_view_get(self):
        """Test que la vista de edición responde correctamente"""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        # Hacer request GET
        response = self.client.get(reverse('sales:client_update', kwargs={'pk': self.client_obj.pk}))
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_form.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], ClientForm)
    
    def test_client_update_view_post_valid(self):
        """Test que la vista de edición acepta datos válidos"""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        # Datos válidos
        form_data = {
            'name': 'Updated Test Client',
            'code': 'UPD001',
            'email': 'updated@example.com',
            'phone': '987654321',
            'is_active': True
        }
        
        # Hacer request POST
        response = self.client.post(
            reverse('sales:client_update', kwargs={'pk': self.client_obj.pk}), 
            form_data
        )
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el cliente fue actualizado
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.name, 'Updated Test Client')
        self.assertEqual(self.client_obj.email, 'updated@example.com')
    
    def test_client_list_view(self):
        """Test que la vista de lista responde correctamente"""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        # Hacer request GET
        response = self.client.get(reverse('sales:client_list'))
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_list.html')
        self.assertIn('clients', response.context)
        self.assertIn(self.client_obj, response.context['clients'])
    
    def test_client_detail_view(self):
        """Test que la vista de detalle responde correctamente"""
        # Autenticar usuario
        self.client.force_login(self.user)
        
        # Hacer request GET
        response = self.client.get(reverse('sales:client_detail', kwargs={'pk': self.client_obj.pk}))
        
        # Verificar respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_detail.html')
        self.assertIn('client', response.context)
        self.assertEqual(response.context['client'], self.client_obj)


class ClientModelTestCase(TestCase):
    """Tests para el modelo Client"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre="Test Company",
            identificador_fiscal="12345678"
        )
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Test Branch"
        )
    
    def test_client_creation(self):
        """Test que se puede crear un cliente"""
        client = Client.objects.create(
            name="Test Client",
            code="TEST001",
            email="test@example.com",
            phone="123456789",
            is_active=True
        )
        
        self.assertEqual(client.name, "Test Client")
        self.assertEqual(client.code, "TEST001")
        self.assertEqual(client.email, "test@example.com")
        self.assertTrue(client.is_active)
    
    def test_client_str_representation(self):
        """Test la representación string del cliente"""
        client = Client.objects.create(
            name="Test Client",
            code="TEST001"
        )
        
        self.assertEqual(str(client), "Test Client")
    
    def test_client_get_full_address(self):
        """Test el método get_full_address"""
        client = Client.objects.create(
            name="Test Client",
            address="123 Test Street",
            city="Test City",
            state="Test State",
            postal_code="12345",
            country="Argentina"
        )
        
        expected_address = "123 Test Street, Test City, Test State, 12345, Argentina"
        self.assertEqual(client.get_full_address(), expected_address)
    
    def test_client_get_contact_info(self):
        """Test el método get_contact_info"""
        client = Client.objects.create(
            name="Test Client",
            contact_person="John Doe",
            email="test@example.com",
            phone="123456789",
            mobile="555123456"
        )
        
        contact_info = client.get_contact_info()
        self.assertIn("John Doe", contact_info)
        self.assertIn("test@example.com", contact_info)
        self.assertIn("123456789", contact_info)
        self.assertIn("555123456", contact_info) 