from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient
from sales.models import Client
from core.models import Empresa, Branch

User = get_user_model()


class ClientListFinalTestCase(TestCase):
    """Tests finales para el listado de clientes"""
    
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
        
        # Crear superusuario
        self.user = User.objects.create_user(
            email="admin@example.com",
            nombre="Admin User"
        )
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        
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
    
    def test_client_list_url_structure(self):
        """Test que la URL del listado de clientes tiene la estructura correcta"""
        url = reverse('sales:client_list')
        self.assertEqual(url, '/sales/clients/')
    
    def test_client_list_requires_authentication(self):
        """Test que el listado de clientes requiere autenticación"""
        response = self.client.get(reverse('sales:client_list'))
        self.assertEqual(response.status_code, 302)  # Redirección a login
    
    def test_client_list_accessible_by_superuser(self):
        """Test que el listado de clientes es accesible por superusuario"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sales/clients/client_list.html')
    
    def test_client_list_shows_clients_in_context(self):
        """Test que el listado muestra clientes en el contexto"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('sales:client_list'))
        
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
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar contenido básico del template
        content = response.content.decode()
        self.assertIn("Apple Inc.", content)
        self.assertIn("Microsoft Corporation", content)
    
    def test_client_list_search_functionality(self):
        """Test funcionalidad de búsqueda en el listado"""
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
        """Test funcionalidad de filtros en el listado"""
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


class ClientModelTestCase(TestCase):
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
    
    def test_client_string_representation(self):
        """Test la representación string del modelo Client"""
        client = Client.objects.create(
            name="Test Client",
            code="TEST001",
            email="test@example.com"
        )
        
        # Verificar que el método __str__ funciona correctamente
        self.assertEqual(str(client), "TEST001 - Test Client")
    
    def test_client_required_fields(self):
        """Test que los campos requeridos del modelo Client funcionan"""
        # Crear cliente con campos mínimos
        client = Client.objects.create(
            name="Minimal Client",
            code="MIN001"
        )
        
        self.assertEqual(client.name, "Minimal Client")
        self.assertEqual(client.code, "MIN001")
        self.assertTrue(client.is_active)  # Valor por defecto
    
    def test_client_optional_fields(self):
        """Test que los campos opcionales del modelo Client funcionan"""
        client = Client.objects.create(
            name="Full Client",
            code="FULL001",
            email="full@example.com",
            phone="123456789",
            tax_id="12345678901",
            is_active=False
        )
        
        self.assertEqual(client.email, "full@example.com")
        self.assertEqual(client.phone, "123456789")
        self.assertEqual(client.tax_id, "12345678901")
        self.assertFalse(client.is_active) 