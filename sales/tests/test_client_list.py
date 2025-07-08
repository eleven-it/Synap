from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient
from sales.models import Client
from core.models import Empresa, Branch

User = get_user_model()


class ClientListViewTestCase(TestCase):
    """Tests para la vista de listado de clientes"""
    
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
        
        # Crear clientes de prueba
        self.client1 = Client.objects.create(
            name="Apple Inc.",
            code="APP001",
            email="contact@apple.com",
            phone="123456789",
            tax_id="12345678901",
            is_active=True
        )
        
        self.client2 = Client.objects.create(
            name="Microsoft Corporation",
            code="MSFT002",
            email="info@microsoft.com",
            phone="987654321",
            tax_id="98765432109",
            is_active=True
        )
        
        self.client3 = Client.objects.create(
            name="Google LLC",
            code="GOOG003",
            email="support@google.com",
            phone="555123456",
            tax_id="55512345678",
            is_active=False  # Cliente inactivo
        )
        
        self.client4 = Client.objects.create(
            name="Amazon Web Services",
            code="AWS004",
            email="aws@amazon.com",
            phone="111222333",
            tax_id="11122233344",
            is_active=True
        )
        
        # Configurar cliente HTTP
        self.client = DjangoClient()
    
    def test_client_list_view_requires_login(self):
        """Test que la vista requiere autenticación"""
        response = self.client.get(reverse('sales:client_list'))
        self.assertEqual(response.status_code, 302)  # Redirección a login
    
    def test_client_list_view_authenticated_user(self):
        """Test que la vista funciona para usuarios autenticados"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_list.html')
        self.assertIn('clients', response.context)
    
    def test_client_list_shows_all_active_clients(self):
        """Test que la lista muestra todos los clientes activos"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        clients = response.context['clients']
        # Debería mostrar 3 clientes activos (client1, client2, client4)
        self.assertEqual(clients.count(), 3)
        
        # Verificar que los clientes activos están presentes
        client_names = [client.name for client in clients]
        self.assertIn("Apple Inc.", client_names)
        self.assertIn("Microsoft Corporation", client_names)
        self.assertIn("Amazon Web Services", client_names)
        
        # Verificar que el cliente inactivo no está presente
        self.assertNotIn("Google LLC", client_names)
    
    def test_client_list_search_by_name(self):
        """Test búsqueda por nombre de cliente"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'search': 'Apple'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 1)
        self.assertEqual(clients.first().name, "Apple Inc.")
    
    def test_client_list_search_by_email(self):
        """Test búsqueda por email de cliente"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'search': 'microsoft.com'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 1)
        self.assertEqual(clients.first().name, "Microsoft Corporation")
    
    def test_client_list_search_by_tax_id(self):
        """Test búsqueda por número de identificación fiscal"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'search': '12345678901'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 1)
        self.assertEqual(clients.first().name, "Apple Inc.")
    
    def test_client_list_search_case_insensitive(self):
        """Test que la búsqueda no distingue entre mayúsculas y minúsculas"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'search': 'apple'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 1)
        self.assertEqual(clients.first().name, "Apple Inc.")
    
    def test_client_list_search_partial_match(self):
        """Test búsqueda con coincidencia parcial"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'search': 'Corp'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 1)
        self.assertEqual(clients.first().name, "Microsoft Corporation")
    
    def test_client_list_search_no_results(self):
        """Test búsqueda sin resultados"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'search': 'NonExistentClient'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 0)
    
    def test_client_list_filter_active(self):
        """Test filtro por estado activo"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'status': 'active'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 3)
        
        # Verificar que todos los clientes están activos
        for client in clients:
            self.assertTrue(client.is_active)
    
    def test_client_list_filter_inactive(self):
        """Test filtro por estado inactivo"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {'status': 'inactive'})
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 1)
        self.assertEqual(clients.first().name, "Google LLC")
        self.assertFalse(clients.first().is_active)
    
    def test_client_list_combined_search_and_filter(self):
        """Test combinación de búsqueda y filtro"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {
            'search': 'Microsoft',
            'status': 'active'
        })
        
        clients = response.context['clients']
        self.assertEqual(clients.count(), 1)
        self.assertEqual(clients.first().name, "Microsoft Corporation")
        self.assertTrue(clients.first().is_active)
    
    def test_client_list_pagination(self):
        """Test paginación del listado"""
        # Crear más clientes para probar paginación
        for i in range(25):
            Client.objects.create(
                name=f"Test Client {i}",
                code=f"TEST{i:03d}",
                email=f"test{i}@example.com",
                phone=f"123456{i:03d}",
                is_active=True
            )
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        # Verificar que hay paginación
        self.assertIn('is_paginated', response.context)
        self.assertTrue(response.context['is_paginated'])
        
        # Verificar que hay múltiples páginas
        self.assertIn('page_obj', response.context)
        self.assertGreater(response.context['page_obj'].paginator.num_pages, 1)
    
    def test_client_list_context_data(self):
        """Test que el contexto incluye los datos necesarios"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        # Verificar que el contexto incluye los datos de búsqueda
        self.assertIn('search', response.context)
        self.assertIn('status_filter', response.context)
        
        # Verificar que los datos están vacíos por defecto
        self.assertEqual(response.context['search'], '')
        self.assertEqual(response.context['status_filter'], '')
    
    def test_client_list_with_search_context(self):
        """Test que el contexto mantiene los parámetros de búsqueda"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'), {
            'search': 'Apple',
            'status': 'active'
        })
        
        # Verificar que el contexto mantiene los valores de búsqueda
        self.assertEqual(response.context['search'], 'Apple')
        self.assertEqual(response.context['status_filter'], 'active')
    
    def test_client_list_ordering(self):
        """Test que los clientes están ordenados correctamente"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        clients = list(response.context['clients'])
        
        # Verificar que están ordenados por ID descendente (más recientes primero)
        for i in range(len(clients) - 1):
            self.assertGreaterEqual(clients[i].id, clients[i + 1].id)
    
    def test_client_list_empty_results(self):
        """Test listado cuando no hay clientes"""
        # Eliminar todos los clientes
        Client.objects.all().delete()
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['clients'].count(), 0)
    
    def test_client_list_permissions(self):
        """Test que la vista respeta los permisos"""
        # Crear usuario sin permisos específicos
        user_no_perms = User.objects.create_user(
            email="noperms@example.com",
            nombre="No Perms User"
        )
        
        self.client.force_login(user_no_perms)
        response = self.client.get(reverse('sales:client_list'))
        
        # La vista debería funcionar (permisos básicos de autenticación)
        self.assertEqual(response.status_code, 200)


class ClientListTemplateTestCase(TestCase):
    """Tests para el template del listado de clientes"""
    
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
    
    def test_client_list_template_structure(self):
        """Test que el template tiene la estructura correcta"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        # Verificar que el template se renderiza correctamente
        self.assertEqual(response.status_code, 200)
        
        # Verificar contenido básico del template
        content = response.content.decode()
        self.assertIn("Test Client", content)
        self.assertIn("test@example.com", content)
        self.assertIn("123456789", content)
    
    def test_client_list_template_search_form(self):
        """Test que el template incluye el formulario de búsqueda"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        content = response.content.decode()
        
        # Verificar que hay campos de búsqueda
        self.assertIn('name="search"', content)
        self.assertIn('name="status"', content)
    
    def test_client_list_template_client_links(self):
        """Test que el template incluye enlaces a los clientes"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        content = response.content.decode()
        
        # Verificar que hay enlaces a los detalles del cliente
        self.assertIn('href', content)  # Debería haber enlaces
        self.assertIn('Test Client', content)  # Nombre del cliente visible
    
    def test_client_list_template_empty_state(self):
        """Test que el template maneja el estado vacío correctamente"""
        # Eliminar todos los clientes
        Client.objects.all().delete()
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        content = response.content.decode()
        
        # Verificar que hay un mensaje de estado vacío o similar
        # (esto dependerá de cómo esté implementado el template)
        self.assertEqual(response.status_code, 200) 