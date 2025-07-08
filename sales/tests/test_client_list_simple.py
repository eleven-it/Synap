from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from sales.models import Client
from core.models import Empresa, Branch

User = get_user_model()


class SimpleClientListViewTestCase(TestCase):
    """Tests simplificados para la vista de listado de clientes"""
    
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
        
        # Crear usuario con permisos
        self.user = User.objects.create_user(
            email="test@example.com",
            nombre="Test User"
        )
        
        # Asignar permisos de cliente al usuario
        content_type = ContentType.objects.get_for_model(Client)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_client'
        )
        self.user.user_permissions.add(view_permission)
        
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
        
        # Configurar cliente HTTP
        self.client = DjangoClient()
    
    def test_client_list_view_requires_login(self):
        """Test que la vista requiere autenticación"""
        response = self.client.get(reverse('sales:client_list'))
        self.assertEqual(response.status_code, 302)  # Redirección a login
    
    def test_client_list_view_requires_permission(self):
        """Test que la vista requiere permisos específicos"""
        # Crear usuario sin permisos
        user_no_perms = User.objects.create_user(
            email="noperms@example.com",
            nombre="No Perms User"
        )
        
        self.client.force_login(user_no_perms)
        response = self.client.get(reverse('sales:client_list'))
        
        # Debería devolver 403 (Forbidden) o redirigir
        self.assertIn(response.status_code, [302, 403])
    
    def test_client_list_view_authenticated_with_permissions(self):
        """Test que la vista funciona para usuarios autenticados con permisos"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_list.html')
    
    def test_client_list_shows_clients(self):
        """Test que la lista muestra clientes"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el contexto contiene clientes
        if response.context:
            self.assertIn('clients', response.context)
            clients = response.context['clients']
            # Debería mostrar al menos los clientes activos
            self.assertGreaterEqual(clients.count(), 2)
    
    def test_client_list_template_content(self):
        """Test que el template renderiza contenido correcto"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)
        
        # Verificar contenido básico del template
        content = response.content.decode()
        self.assertIn("Apple Inc.", content)
        self.assertIn("Microsoft Corporation", content)
    
    def test_client_list_search_functionality(self):
        """Test funcionalidad básica de búsqueda"""
        self.client.force_login(self.user)
        
        # Búsqueda por nombre
        response = self.client.get(reverse('sales:client_list'), {'search': 'Apple'})
        self.assertEqual(response.status_code, 200)
        
        # Búsqueda por email
        response = self.client.get(reverse('sales:client_list'), {'search': 'microsoft.com'})
        self.assertEqual(response.status_code, 200)
        
        # Búsqueda sin resultados
        response = self.client.get(reverse('sales:client_list'), {'search': 'NonExistentClient'})
        self.assertEqual(response.status_code, 200)
    
    def test_client_list_filter_functionality(self):
        """Test funcionalidad básica de filtros"""
        self.client.force_login(self.user)
        
        # Filtro por estado activo
        response = self.client.get(reverse('sales:client_list'), {'status': 'active'})
        self.assertEqual(response.status_code, 200)
        
        # Filtro por estado inactivo
        response = self.client.get(reverse('sales:client_list'), {'status': 'inactive'})
        self.assertEqual(response.status_code, 200)
    
    def test_client_list_combined_search_and_filter(self):
        """Test combinación de búsqueda y filtro"""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('sales:client_list'), {
            'search': 'Microsoft',
            'status': 'active'
        })
        self.assertEqual(response.status_code, 200)
    
    def test_client_list_empty_results(self):
        """Test listado cuando no hay clientes"""
        # Eliminar todos los clientes
        Client.objects.all().delete()
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        self.assertEqual(response.status_code, 200)
    
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
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que hay paginación si el contexto existe
        if response.context and 'is_paginated' in response.context:
            self.assertTrue(response.context['is_paginated'])


class ClientListURLTestCase(TestCase):
    """Tests para las URLs del listado de clientes"""
    
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
        
        # Crear usuario con permisos
        self.user = User.objects.create_user(
            email="test@example.com",
            nombre="Test User"
        )
        
        # Asignar permisos de cliente al usuario
        content_type = ContentType.objects.get_for_model(Client)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_client'
        )
        self.user.user_permissions.add(view_permission)
        
        # Configurar cliente HTTP
        self.client = DjangoClient()
    
    def test_client_list_url_resolves(self):
        """Test que la URL del listado de clientes se resuelve correctamente"""
        url = reverse('sales:client_list')
        self.assertEqual(url, '/sales/clients/')
    
    def test_client_list_url_accessible(self):
        """Test que la URL del listado de clientes es accesible"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_client_list_url_requires_login(self):
        """Test que la URL del listado de clientes requiere login"""
        response = self.client.get(reverse('sales:client_list'))
        self.assertEqual(response.status_code, 302)  # Redirección a login


class ClientListModelTestCase(TestCase):
    """Tests para el modelo Client en el contexto del listado"""
    
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
    
    def test_client_creation_for_listing(self):
        """Test que se pueden crear clientes para el listado"""
        client = Client.objects.create(
            name="Test Client for Listing",
            code="LIST001",
            email="listing@example.com",
            phone="123456789",
            is_active=True
        )
        
        self.assertEqual(client.name, "Test Client for Listing")
        self.assertEqual(client.code, "LIST001")
        self.assertTrue(client.is_active)
    
    def test_client_ordering_for_listing(self):
        """Test que los clientes se pueden ordenar para el listado"""
        # Crear clientes en orden específico
        client1 = Client.objects.create(name="A Client", code="A001", is_active=True)
        client2 = Client.objects.create(name="B Client", code="B001", is_active=True)
        client3 = Client.objects.create(name="C Client", code="C001", is_active=True)
        
        # Ordenar por nombre
        clients_ordered = Client.objects.order_by('name')
        self.assertEqual(clients_ordered[0], client1)
        self.assertEqual(clients_ordered[1], client2)
        self.assertEqual(clients_ordered[2], client3)
    
    def test_client_filtering_for_listing(self):
        """Test que los clientes se pueden filtrar para el listado"""
        # Crear clientes activos e inactivos
        active_client = Client.objects.create(name="Active Client", is_active=True)
        inactive_client = Client.objects.create(name="Inactive Client", is_active=False)
        
        # Filtrar por estado activo
        active_clients = Client.objects.filter(is_active=True)
        self.assertIn(active_client, active_clients)
        self.assertNotIn(inactive_client, active_clients)
        
        # Filtrar por estado inactivo
        inactive_clients = Client.objects.filter(is_active=False)
        self.assertIn(inactive_client, inactive_clients)
        self.assertNotIn(active_client, inactive_clients)
    
    def test_client_search_for_listing(self):
        """Test que los clientes se pueden buscar para el listado"""
        from django.db.models import Q
        
        # Crear clientes con diferentes nombres
        client1 = Client.objects.create(name="Apple Inc.", email="apple@example.com")
        client2 = Client.objects.create(name="Microsoft Corp", email="ms@example.com")
        client3 = Client.objects.create(name="Google LLC", email="google@example.com")
        
        # Búsqueda por nombre
        search_results = Client.objects.filter(Q(name__icontains='Apple'))
        self.assertIn(client1, search_results)
        self.assertNotIn(client2, search_results)
        self.assertNotIn(client3, search_results)
        
        # Búsqueda por email
        search_results = Client.objects.filter(Q(email__icontains='ms'))
        self.assertIn(client2, search_results)
        self.assertNotIn(client1, search_results)
        self.assertNotIn(client3, search_results) 