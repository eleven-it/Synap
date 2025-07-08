from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from sales.models import Client
from core.models import Empresa, Branch

User = get_user_model()


class ClientListDebugTestCase(TestCase):
    """Tests de debug para la vista de listado de clientes"""
    
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
        self.test_client = Client.objects.create(
            name="Test Client",
            code="TEST001",
            email="test@example.com",
            phone="123456789",
            is_active=True
        )
        
        # Configurar cliente HTTP
        self.client = DjangoClient()
    
    def test_client_list_url_resolves(self):
        """Test que la URL se resuelve correctamente"""
        url = reverse('sales:client_list')
        self.assertEqual(url, '/sales/clients/')
    
    def test_client_list_requires_login(self):
        """Test que requiere login"""
        response = self.client.get(reverse('sales:client_list'))
        self.assertEqual(response.status_code, 302)
    
    def test_client_list_with_superuser(self):
        """Test con superusuario"""
        # Hacer al usuario superusuario
        self.user.is_superuser = True
        self.user.save()
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        print(f"Status code: {response.status_code}")
        print(f"Response content: {response.content[:500]}")
        
        self.assertEqual(response.status_code, 200)
    
    def test_client_list_with_permissions(self):
        """Test con permisos específicos"""
        # Asignar permisos de cliente al usuario
        content_type = ContentType.objects.get_for_model(Client)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_client'
        )
        self.user.user_permissions.add(view_permission)
        
        # Verificar que el usuario tiene el permiso
        self.assertTrue(self.user.has_perm('sales.view_client'))
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        print(f"Status code: {response.status_code}")
        if response.status_code == 302:
            print(f"Redirect URL: {response.url}")
        
        self.assertEqual(response.status_code, 200)
    
    def test_client_list_template_exists(self):
        """Test que el template existe"""
        from django.template.loader import get_template
        try:
            template = get_template('sales/clients/client_list.html')
            self.assertIsNotNone(template)
        except Exception as e:
            self.fail(f"Template no existe: {e}")
    
    def test_client_model_has_required_fields(self):
        """Test que el modelo Client tiene los campos requeridos"""
        client = Client.objects.first()
        self.assertIsNotNone(client)
        self.assertIsNotNone(client.name)
        self.assertIsNotNone(client.code)
    
    def test_client_list_view_class_exists(self):
        """Test que la vista ClientListView existe"""
        from sales.views import ClientListView
        self.assertIsNotNone(ClientListView)
    
    def test_client_list_view_permissions(self):
        """Test los permisos de la vista"""
        from sales.views import ClientListView
        self.assertEqual(ClientListView.permission_required, 'sales.view_client') 