from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
import json

from core.models import Empresa, Branch, Currency, UnitOfMeasure
from inventory.models import Product, ProductVariant, Category
from purchases.models import (
    Supplier, ApprovalWorkflow, ApprovalLevel, PurchaseRequest, PurchaseRequestLine,
    PurchaseOrder, PurchaseOrderLine, PurchaseQuotation, PurchaseQuotationLine,
    PurchaseReceipt, SupplierRating
)

User = get_user_model()


class PurchaseAPITest(TestCase):
    """Pruebas para las APIs del módulo de compras"""
    
    def setUp(self):
        """Configuración inicial para todas las pruebas"""
        self.client = APIClient()
        
        # Crear empresa y branch
        self.empresa = Empresa.objects.create(
            name="Empresa Test",
            tax_id="12345678"
        )
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        
        # Crear moneda y unidad de medida
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.uom = UnitOfMeasure.objects.create(
            empresa=self.empresa,
            name="Unidad",
            code="U"
        )
        
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear categoría y producto
        self.category = Category.objects.create(
            empresa=self.empresa,
            name="Categoría Test"
        )
        self.product = Product.objects.create(
            empresa=self.empresa,
            name="Producto Test",
            category=self.category
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            name="Variante Test",
            sku="SKU001"
        )
        
        # Crear proveedor
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            code="PROV001",
            email="proveedor@test.com"
        )
        
        # Autenticar usuario
        self.client.force_authenticate(user=self.user)


class SupplierAPITest(PurchaseAPITest):
    """Pruebas para la API de proveedores"""
    
    def test_supplier_list_api(self):
        """Probar listado de proveedores via API"""
        url = reverse('purchases:api:supplier-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Proveedor Test')
    
    def test_supplier_create_api(self):
        """Probar creación de proveedor via API"""
        url = reverse('purchases:api:supplier-list')
        data = {
            'name': 'Nuevo Proveedor API',
            'code': 'PROV002',
            'tax_id': '87654321',
            'email': 'nuevo@api.com',
            'phone': '+1234567890',
            'address': 'Dirección API',
            'city': 'Ciudad API',
            'country': 'País API',
            'is_active': True
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.count(), 2)
        
        supplier = Supplier.objects.get(code='PROV002')
        self.assertEqual(supplier.name, 'Nuevo Proveedor API')
    
    def test_supplier_detail_api(self):
        """Probar detalle de proveedor via API"""
        url = reverse('purchases:api:supplier-detail', kwargs={'pk': self.supplier.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Proveedor Test')
        self.assertEqual(response.data['code'], 'PROV001')
    
    def test_supplier_update_api(self):
        """Probar actualización de proveedor via API"""
        url = reverse('purchases:api:supplier-detail', kwargs={'pk': self.supplier.pk})
        data = {
            'name': 'Proveedor Actualizado API',
            'code': 'PROV001',
            'email': 'actualizado@api.com'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.name, 'Proveedor Actualizado API')
    
    def test_supplier_delete_api(self):
        """Probar eliminación de proveedor via API"""
        url = reverse('purchases:api:supplier-detail', kwargs={'pk': self.supplier.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Supplier.objects.count(), 0)
    
    def test_supplier_search_api(self):
        """Probar búsqueda de proveedores via API"""
        # Crear otro proveedor
        Supplier.objects.create(
            empresa=self.empresa,
            name="Otro Proveedor",
            code="PROV003"
        )
        
        url = reverse('purchases:api:supplier-list')
        response = self.client.get(url, {'search': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Proveedor Test')
    
    def test_supplier_filter_api(self):
        """Probar filtros de proveedores via API"""
        # Crear proveedor inactivo
        Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Inactivo",
            code="PROV004",
            is_active=False
        )
        
        url = reverse('purchases:api:supplier-list')
        response = self.client.get(url, {'is_active': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue(response.data['results'][0]['is_active'])


class PurchaseRequestAPITest(PurchaseAPITest):
    """Pruebas para la API de solicitudes de compra"""
    
    def setUp(self):
        super().setUp()
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test API",
            description="Descripción de prueba API",
            priority='medium',
            required_date=timezone.now().date() + timedelta(days=30),
            requested_by=self.user,
            currency=self.currency,
            supplier=self.supplier
        )
    
    def test_request_list_api(self):
        """Probar listado de solicitudes via API"""
        url = reverse('purchases:api:request-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Solicitud Test API')
    
    def test_request_create_api(self):
        """Probar creación de solicitud via API"""
        url = reverse('purchases:api:request-list')
        data = {
            'title': 'Nueva Solicitud API',
            'description': 'Descripción de nueva solicitud API',
            'priority': 'high',
            'required_date': (timezone.now().date() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'supplier': self.supplier.pk,
            'currency': self.currency.pk,
            'lines': [
                {
                    'product_variant': self.product_variant.pk,
                    'quantity': 10,
                    'estimated_unit_price': '100.00',
                    'unit_of_measure': self.uom.pk,
                    'description': 'Línea de prueba API'
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PurchaseRequest.objects.count(), 2)
        
        new_request = PurchaseRequest.objects.get(title='Nueva Solicitud API')
        self.assertEqual(new_request.priority, 'high')
        self.assertEqual(new_request.lines.count(), 1)
    
    def test_request_detail_api(self):
        """Probar detalle de solicitud via API"""
        url = reverse('purchases:api:request-detail', kwargs={'pk': self.request.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Solicitud Test API')
        self.assertEqual(response.data['status'], 'draft')
    
    def test_request_update_api(self):
        """Probar actualización de solicitud via API"""
        url = reverse('purchases:api:request-detail', kwargs={'pk': self.request.pk})
        data = {
            'title': 'Solicitud Actualizada API',
            'description': 'Descripción actualizada',
            'priority': 'high',
            'required_date': (timezone.now().date() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'supplier': self.supplier.pk,
            'currency': self.currency.pk
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.request.refresh_from_db()
        self.assertEqual(self.request.title, 'Solicitud Actualizada API')
        self.assertEqual(self.request.priority, 'high')
    
    def test_request_submit_action_api(self):
        """Probar acción de enviar solicitud a aprobación via API"""
        url = reverse('purchases:api:request-submit', kwargs={'pk': self.request.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, 'pending_approval')
    
    def test_request_approve_action_api(self):
        """Probar acción de aprobar solicitud via API"""
        # Primero enviar a aprobación
        self.request.status = 'pending_approval'
        self.request.save()
        
        url = reverse('purchases:api:request-approve', kwargs={'pk': self.request.pk})
        data = {'comments': 'Aprobado via API'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, 'approved')
    
    def test_request_reject_action_api(self):
        """Probar acción de rechazar solicitud via API"""
        # Primero enviar a aprobación
        self.request.status = 'pending_approval'
        self.request.save()
        
        url = reverse('purchases:api:request-reject', kwargs={'pk': self.request.pk})
        data = {'rejection_reason': 'Rechazado via API'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, 'rejected')
    
    def test_request_filter_api(self):
        """Probar filtros de solicitudes via API"""
        # Crear solicitud con diferente prioridad
        PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Alta Prioridad",
            priority='high',
            requested_by=self.user,
            currency=self.currency
        )
        
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'priority': 'high'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['priority'], 'high')


class PurchaseOrderAPITest(PurchaseAPITest):
    """Pruebas para la API de órdenes de compra"""
    
    def setUp(self):
        super().setUp()
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            status='approved'
        )
        
        self.order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            purchase_request=self.request,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
    
    def test_order_list_api(self):
        """Probar listado de órdenes via API"""
        url = reverse('purchases:api:order-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['order_number'], self.order.order_number)
    
    def test_order_create_api(self):
        """Probar creación de orden via API"""
        url = reverse('purchases:api:order-list')
        data = {
            'supplier': self.supplier.pk,
            'purchase_request': self.request.pk,
            'expected_delivery_date': (timezone.now().date() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'currency': self.currency.pk,
            'lines': [
                {
                    'product_variant': self.product_variant.pk,
                    'quantity': 10,
                    'unit_price': '100.00',
                    'unit_of_measure': self.uom.pk
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PurchaseOrder.objects.count(), 2)
        
        new_order = PurchaseOrder.objects.latest('id')
        self.assertEqual(new_order.supplier, self.supplier)
        self.assertEqual(new_order.lines.count(), 1)
    
    def test_order_detail_api(self):
        """Probar detalle de orden via API"""
        url = reverse('purchases:api:order-detail', kwargs={'pk': self.order.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order_number'], self.order.order_number)
        self.assertEqual(response.data['status'], 'draft')
    
    def test_order_send_action_api(self):
        """Probar acción de enviar orden via API"""
        url = reverse('purchases:api:order-send', kwargs={'pk': self.order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'sent')
    
    def test_order_confirm_action_api(self):
        """Probar acción de confirmar orden via API"""
        # Primero enviar la orden
        self.order.status = 'sent'
        self.order.save()
        
        url = reverse('purchases:api:order-confirm', kwargs={'pk': self.order.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')


class PurchaseQuotationAPITest(PurchaseAPITest):
    """Pruebas para la API de cotizaciones"""
    
    def setUp(self):
        super().setUp()
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
        
        self.quotation = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_request=self.request,
            quotation_date=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=30),
            delivery_time=15
        )
    
    def test_quotation_list_api(self):
        """Probar listado de cotizaciones via API"""
        url = reverse('purchases:api:quotation-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['quotation_number'], self.quotation.quotation_number)
    
    def test_quotation_create_api(self):
        """Probar creación de cotización via API"""
        url = reverse('purchases:api:quotation-list')
        data = {
            'supplier': self.supplier.pk,
            'purchase_request': self.request.pk,
            'quotation_date': timezone.now().date().strftime('%Y-%m-%d'),
            'valid_until': (timezone.now().date() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'delivery_time': 20,
            'lines': [
                {
                    'product_variant': self.product_variant.pk,
                    'quantity': 10,
                    'unit_price': '95.00',
                    'unit_of_measure': self.uom.pk
                }
            ]
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PurchaseQuotation.objects.count(), 2)
        
        new_quotation = PurchaseQuotation.objects.latest('id')
        self.assertEqual(new_quotation.supplier, self.supplier)
        self.assertEqual(new_quotation.lines.count(), 1)
    
    def test_quotation_detail_api(self):
        """Probar detalle de cotización via API"""
        url = reverse('purchases:api:quotation-detail', kwargs={'pk': self.quotation.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quotation_number'], self.quotation.quotation_number)
        self.assertEqual(response.data['status'], 'draft')
    
    def test_quotation_compare_api(self):
        """Probar comparación de cotizaciones via API"""
        # Crear otra cotización
        quotation2 = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_request=self.request,
            quotation_date=timezone.now().date()
        )
        
        url = reverse('purchases:api:quotation-compare', kwargs={'request_pk': self.request.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Dos cotizaciones


class PurchaseReceiptAPITest(PurchaseAPITest):
    """Pruebas para la API de recepciones"""
    
    def setUp(self):
        super().setUp()
        self.order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        
        self.order_line = PurchaseOrderLine.objects.create(
            purchase_order=self.order,
            product_variant=self.product_variant,
            quantity=10,
            unit_price=Decimal('100.00')
        )
        
        self.receipt = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            purchase_order_line=self.order_line,
            quantity=5,
            unit_cost=Decimal('100.00'),
            received_by=self.user,
            receipt_date=timezone.now().date()
        )
    
    def test_receipt_list_api(self):
        """Probar listado de recepciones via API"""
        url = reverse('purchases:api:receipt-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['receipt_number'], self.receipt.receipt_number)
    
    def test_receipt_create_api(self):
        """Probar creación de recepción via API"""
        url = reverse('purchases:api:receipt-list')
        data = {
            'purchase_order_line': self.order_line.pk,
            'quantity': 3,
            'unit_cost': '100.00',
            'receipt_date': timezone.now().date().strftime('%Y-%m-%d'),
            'quality_score': 8,
            'lot_number': 'LOT001'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PurchaseReceipt.objects.count(), 2)
        
        new_receipt = PurchaseReceipt.objects.latest('id')
        self.assertEqual(new_receipt.quantity, 3)
        self.assertEqual(new_receipt.quality_score, 8)
    
    def test_receipt_detail_api(self):
        """Probar detalle de recepción via API"""
        url = reverse('purchases:api:receipt-detail', kwargs={'pk': self.receipt.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['receipt_number'], self.receipt.receipt_number)
        self.assertEqual(response.data['status'], 'draft')
    
    def test_receipt_approve_action_api(self):
        """Probar acción de aprobar recepción via API"""
        url = reverse('purchases:api:receipt-approve', kwargs={'pk': self.receipt.pk})
        data = {'quality_score': 9, 'comments': 'Aprobado via API'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.status, 'approved')
        self.assertEqual(self.receipt.quality_score, 9)


class SupplierRatingAPITest(PurchaseAPITest):
    """Pruebas para la API de evaluaciones de proveedores"""
    
    def test_rating_list_api(self):
        """Probar listado de evaluaciones via API"""
        # Crear una evaluación
        rating = SupplierRating.objects.create(
            supplier=self.supplier,
            evaluated_by=self.user,
            overall_score=8.5
        )
        
        url = reverse('purchases:api:rating-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['overall_score'], 8.5)
    
    def test_rating_create_api(self):
        """Probar creación de evaluación via API"""
        url = reverse('purchases:api:rating-list')
        data = {
            'supplier': self.supplier.pk,
            'overall_score': 8.5,
            'quality_score': 9.0,
            'delivery_score': 8.0,
            'communication_score': 8.5,
            'price_score': 7.5,
            'comments': 'Excelente proveedor via API'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupplierRating.objects.count(), 1)
        
        rating = SupplierRating.objects.first()
        self.assertEqual(rating.overall_score, 8.5)
        self.assertEqual(rating.comments, 'Excelente proveedor via API')
    
    def test_rating_detail_api(self):
        """Probar detalle de evaluación via API"""
        rating = SupplierRating.objects.create(
            supplier=self.supplier,
            evaluated_by=self.user,
            overall_score=8.5
        )
        
        url = reverse('purchases:api:rating-detail', kwargs={'pk': rating.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['overall_score'], 8.5)
        self.assertEqual(response.data['rating_class'], 'good')


class DashboardAPITest(PurchaseAPITest):
    """Pruebas para la API del dashboard"""
    
    def test_dashboard_metrics_api(self):
        """Probar métricas del dashboard via API"""
        # Crear datos de prueba
        PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
        
        PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        
        url = reverse('purchases:api:dashboard-metrics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('requests', response.data)
        self.assertIn('orders', response.data)
        self.assertIn('spending', response.data)
        self.assertIn('suppliers', response.data)
        self.assertIn('delivery', response.data)
        self.assertIn('alerts', response.data)
    
    def test_spending_trends_api(self):
        """Probar tendencias de gastos via API"""
        url = reverse('purchases:api:spending-trends')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_supplier_performance_api(self):
        """Probar rendimiento de proveedores via API"""
        url = reverse('purchases:api:supplier-performance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
    
    def test_category_spending_api(self):
        """Probar gastos por categoría via API"""
        url = reverse('purchases:api:category-spending')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class AuthenticationAPITest(PurchaseAPITest):
    """Pruebas de autenticación para APIs"""
    
    def test_unauthenticated_access(self):
        """Probar acceso sin autenticación"""
        self.client.force_authenticate(user=None)
        
        urls_to_test = [
            reverse('purchases:api:supplier-list'),
            reverse('purchases:api:request-list'),
            reverse('purchases:api:order-list'),
            reverse('purchases:api:quotation-list'),
            reverse('purchases:api:receipt-list'),
        ]
        
        for url in urls_to_test:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_permission_required_actions(self):
        """Probar acciones que requieren permisos específicos"""
        # Crear usuario sin permisos específicos
        user_no_perms = User.objects.create_user(
            username='noperms',
            email='noperms@example.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=user_no_perms)
        
        # Intentar aprobar solicitud
        url = reverse('purchases:api:request-approve', kwargs={'pk': 1})
        response = self.client.post(url, {'comments': 'Aprobado'}, format='json')
        
        # Debería devolver 403
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PaginationAPITest(PurchaseAPITest):
    """Pruebas de paginación para APIs"""
    
    def setUp(self):
        super().setUp()
        # Crear múltiples proveedores para probar paginación
        for i in range(25):
            Supplier.objects.create(
                empresa=self.empresa,
                name=f"Proveedor {i}",
                code=f"PROV{i:03d}"
            )
    
    def test_supplier_pagination(self):
        """Probar paginación en listado de proveedores"""
        url = reverse('purchases:api:supplier-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        # Verificar que hay paginación
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(len(response.data['results']), 20)  # Tamaño de página por defecto
    
    def test_supplier_pagination_page_size(self):
        """Probar cambio de tamaño de página"""
        url = reverse('purchases:api:supplier-list')
        response = self.client.get(url, {'page_size': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)


class FilteringAPITest(PurchaseAPITest):
    """Pruebas de filtrado para APIs"""
    
    def setUp(self):
        super().setUp()
        # Crear solicitudes con diferentes estados
        self.request1 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Draft",
            requested_by=self.user,
            currency=self.currency,
            status='draft'
        )
        
        self.request2 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Pending",
            requested_by=self.user,
            currency=self.currency,
            status='pending_approval'
        )
    
    def test_request_filter_by_status(self):
        """Probar filtro por estado en solicitudes"""
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'status': 'draft'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'draft')
    
    def test_request_filter_by_priority(self):
        """Probar filtro por prioridad en solicitudes"""
        self.request1.priority = 'high'
        self.request1.save()
        
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'priority': 'high'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['priority'], 'high')
    
    def test_request_filter_by_supplier(self):
        """Probar filtro por proveedor en solicitudes"""
        self.request1.supplier = self.supplier
        self.request1.save()
        
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'supplier': self.supplier.pk})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['supplier'], self.supplier.pk)
    
    def test_request_search(self):
        """Probar búsqueda en solicitudes"""
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'search': 'Draft'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('Draft', response.data['results'][0]['title'])


class OrderingAPITest(PurchaseAPITest):
    """Pruebas de ordenamiento para APIs"""
    
    def setUp(self):
        super().setUp()
        # Crear solicitudes con diferentes fechas
        self.request1 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Antigua",
            requested_by=self.user,
            currency=self.currency,
            request_date=timezone.now().date() - timedelta(days=10)
        )
        
        self.request2 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Reciente",
            requested_by=self.user,
            currency=self.currency,
            request_date=timezone.now().date()
        )
    
    def test_request_ordering_by_date_asc(self):
        """Probar ordenamiento por fecha ascendente"""
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'ordering': 'request_date'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        # La primera debería ser la más antigua
        self.assertIn('Antigua', response.data['results'][0]['title'])
    
    def test_request_ordering_by_date_desc(self):
        """Probar ordenamiento por fecha descendente"""
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'ordering': '-request_date'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        # La primera debería ser la más reciente
        self.assertIn('Reciente', response.data['results'][0]['title'])
    
    def test_request_ordering_by_title(self):
        """Probar ordenamiento por título"""
        url = reverse('purchases:api:request-list')
        response = self.client.get(url, {'ordering': 'title'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        # Orden alfabético
        self.assertIn('Antigua', response.data['results'][0]['title'])
        self.assertIn('Reciente', response.data['results'][1]['title']) 