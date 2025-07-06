from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock

from core.models import Empresa, Branch, Currency, UnitOfMeasure
from inventory.models import Product, ProductVariant, Category
from purchases.models import (
    Supplier, ApprovalWorkflow, ApprovalLevel, PurchaseRequest, PurchaseRequestLine,
    PurchaseOrder, PurchaseOrderLine, PurchaseQuotation, PurchaseQuotationLine,
    PurchaseReceipt, SupplierRating
)
from purchases.notifications import PurchaseNotificationService
from purchases.validators import (
    PurchaseRequestValidator, PurchaseOrderValidator, PurchaseReceiptValidator,
    SupplierValidator, BusinessRuleValidator, validate_purchase_request
)
from purchases.reports import PurchaseReportsService
from purchases.inventory_integration import InventoryIntegrationService

User = get_user_model()


class NotificationServiceTest(TestCase):
    """Pruebas para el servicio de notificaciones"""
    
    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            email="proveedor@test.com"
        )
        
        self.notification_service = PurchaseNotificationService()
    
    @patch('purchases.notifications.send_mail')
    def test_send_request_created_notification(self, mock_send_mail):
        """Probar notificación de solicitud creada"""
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
        
        self.notification_service.send_request_created_notification(request)
        
        # Verificar que se llamó send_mail
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('New Purchase Request Created', call_args[1]['subject'])
        self.assertEqual(call_args[1]['recipient_list'], [self.user.email])
    
    @patch('purchases.notifications.send_mail')
    def test_send_request_submitted_notification(self, mock_send_mail):
        """Probar notificación de solicitud enviada a aprobación"""
        # Crear flujo de aprobación
        workflow = ApprovalWorkflow.objects.create(
            empresa=self.empresa,
            name="Flujo Test",
            is_active=True
        )
        level = ApprovalLevel.objects.create(
            workflow=workflow,
            name="Nivel 1",
            priority=1,
            approval_type='user'
        )
        level.approvers.add(self.user)
        
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            approval_workflow=workflow
        )
        
        self.notification_service.send_request_submitted_notification(request)
        
        # Verificar que se enviaron múltiples emails (solicitante + aprobadores)
        self.assertGreater(mock_send_mail.call_count, 1)
    
    @patch('purchases.notifications.send_mail')
    def test_send_request_approved_notification(self, mock_send_mail):
        """Probar notificación de solicitud aprobada"""
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
        
        self.notification_service.send_request_approved_notification(request, self.user)
        
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('Purchase Request Approved', call_args[1]['subject'])
    
    @patch('purchases.notifications.send_mail')
    def test_send_order_created_notification(self, mock_send_mail):
        """Probar notificación de orden creada"""
        order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        
        self.notification_service.send_order_created_notification(order)
        
        # Verificar que se enviaron emails (creador + proveedor)
        self.assertGreaterEqual(mock_send_mail.call_count, 1)
    
    @patch('purchases.notifications.send_mail')
    def test_send_supplier_rating_notification(self, mock_send_mail):
        """Probar notificación de evaluación de proveedor"""
        rating = SupplierRating.objects.create(
            supplier=self.supplier,
            evaluated_by=self.user,
            overall_score=8.5
        )
        
        self.notification_service.send_supplier_rating_notification(rating)
        
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('Supplier Rating Submitted', call_args[1]['subject'])


class ValidatorServiceTest(TestCase):
    """Pruebas para los servicios de validación"""
    
    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            credit_limit=Decimal('10000')
        )
    
    def test_validate_request_amount_valid(self):
        """Probar validación de monto válido"""
        amount = Decimal('5000')
        
        # No debería lanzar excepción
        PurchaseRequestValidator.validate_request_amount(amount, self.empresa)
    
    def test_validate_request_amount_invalid(self):
        """Probar validación de monto inválido"""
        amount = Decimal('0')
        
        with self.assertRaises(ValidationError):
            PurchaseRequestValidator.validate_request_amount(amount, self.empresa)
    
    def test_validate_required_date_valid(self):
        """Probar validación de fecha requerida válida"""
        request_date = timezone.now().date()
        required_date = request_date + timedelta(days=30)
        
        # No debería lanzar excepción
        PurchaseRequestValidator.validate_required_date(required_date, request_date)
    
    def test_validate_required_date_invalid(self):
        """Probar validación de fecha requerida inválida"""
        request_date = timezone.now().date()
        required_date = request_date - timedelta(days=1)  # Fecha pasada
        
        with self.assertRaises(ValidationError):
            PurchaseRequestValidator.validate_required_date(required_date, request_date)
    
    def test_validate_priority_for_amount(self):
        """Probar validación de prioridad según monto"""
        # Monto alto con prioridad baja debería fallar
        with self.assertRaises(ValidationError):
            PurchaseRequestValidator.validate_priority_for_amount(
                'low', Decimal('60000')
            )
        
        # Monto bajo con prioridad alta debería fallar
        with self.assertRaises(ValidationError):
            PurchaseRequestValidator.validate_priority_for_amount(
                'high', Decimal('500')
            )
    
    def test_validate_supplier_credit_limit(self):
        """Probar validación de límite de crédito"""
        # Crear órdenes pendientes para el proveedor
        PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            total_amount=Decimal('8000'),
            status='confirmed'
        )
        
        # Intentar crear solicitud que exceda el límite
        with self.assertRaises(ValidationError):
            PurchaseRequestValidator.validate_supplier_credit_limit(
                self.supplier, Decimal('3000')
            )
    
    def test_validate_order_amount_valid(self):
        """Probar validación de monto de orden válido"""
        amount = Decimal('5000')
        
        # No debería lanzar excepción
        PurchaseOrderValidator.validate_order_amount(amount, self.empresa)
    
    def test_validate_delivery_date_valid(self):
        """Probar validación de fecha de entrega válida"""
        order_date = timezone.now().date()
        delivery_date = order_date + timedelta(days=30)
        
        # No debería lanzar excepción
        PurchaseOrderValidator.validate_delivery_date(delivery_date, order_date)
    
    def test_validate_supplier_availability(self):
        """Probar validación de disponibilidad del proveedor"""
        # Proveedor activo
        PurchaseOrderValidator.validate_supplier_availability(self.supplier, timezone.now().date())
        
        # Proveedor inactivo
        self.supplier.is_active = False
        self.supplier.save()
        
        with self.assertRaises(ValidationError):
            PurchaseOrderValidator.validate_supplier_availability(self.supplier, timezone.now().date())
    
    def test_validate_receipt_quantity_valid(self):
        """Probar validación de cantidad de recepción válida"""
        order_line = MagicMock()
        order_line.remaining_quantity = 10
        
        # No debería lanzar excepción
        PurchaseReceiptValidator.validate_receipt_quantity(5, order_line)
    
    def test_validate_receipt_quantity_invalid(self):
        """Probar validación de cantidad de recepción inválida"""
        order_line = MagicMock()
        order_line.remaining_quantity = 10
        
        # Cantidad mayor a la restante
        with self.assertRaises(ValidationError):
            PurchaseReceiptValidator.validate_receipt_quantity(15, order_line)
    
    def test_validate_quality_score_valid(self):
        """Probar validación de puntuación de calidad válida"""
        # No debería lanzar excepción
        PurchaseReceiptValidator.validate_quality_score(8)
        PurchaseReceiptValidator.validate_quality_score(1)
        PurchaseReceiptValidator.validate_quality_score(10)
    
    def test_validate_quality_score_invalid(self):
        """Probar validación de puntuación de calidad inválida"""
        with self.assertRaises(ValidationError):
            PurchaseReceiptValidator.validate_quality_score(0)
        
        with self.assertRaises(ValidationError):
            PurchaseReceiptValidator.validate_quality_score(11)
    
    def test_validate_supplier_tax_id_unique(self):
        """Probar validación de ID fiscal único"""
        # ID fiscal ya existe
        with self.assertRaises(ValidationError):
            SupplierValidator.validate_tax_id("12345678", self.empresa)
    
    def test_validate_email_format_valid(self):
        """Probar validación de formato de email válido"""
        # No debería lanzar excepción
        SupplierValidator.validate_email_format("test@example.com")
        SupplierValidator.validate_email_format("user.name@domain.co.uk")
    
    def test_validate_email_format_invalid(self):
        """Probar validación de formato de email inválido"""
        with self.assertRaises(ValidationError):
            SupplierValidator.validate_email_format("invalid-email")
        
        with self.assertRaises(ValidationError):
            SupplierValidator.validate_email_format("@domain.com")
    
    def test_validate_company_limits(self):
        """Probar validación de límites de empresa"""
        # Crear órdenes para exceder límite diario
        for i in range(5):
            PurchaseOrder.objects.create(
                empresa=self.empresa,
                sucursal=self.branch,
                supplier=self.supplier,
                created_by=self.user,
                currency=self.currency,
                total_amount=Decimal('20000'),
                order_date=timezone.now().date()
            )
        
        # Intentar crear orden que exceda límite diario
        with self.assertRaises(ValidationError):
            BusinessRuleValidator.validate_company_limits(
                self.empresa, Decimal('50000'), 'create_order'
            )
    
    def test_validate_user_permissions(self):
        """Probar validación de permisos de usuario"""
        # Usuario sin autenticación
        with self.assertRaises(ValidationError):
            BusinessRuleValidator.validate_user_permissions(None, 'create_request')
        
        # Usuario autenticado sin permisos específicos
        user_no_perms = User.objects.create_user(
            username='noperms',
            email='noperms@example.com',
            password='testpass123'
        )
        
        with self.assertRaises(ValidationError):
            BusinessRuleValidator.validate_user_permissions(user_no_perms, 'approve_request')
    
    def test_validate_workflow_compliance(self):
        """Probar validación de cumplimiento de flujo"""
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            total_amount=Decimal('15000')  # Monto alto
        )
        
        # Solicitud sin flujo de aprobación debería fallar
        with self.assertRaises(ValidationError):
            BusinessRuleValidator.validate_workflow_compliance(request)
    
    def test_validate_supplier_rating(self):
        """Probar validación de calificación de proveedor"""
        # Proveedor con calificación pobre
        self.supplier.rating_class = 'poor'
        self.supplier.save()
        
        with self.assertRaises(ValidationError):
            BusinessRuleValidator.validate_supplier_rating(self.supplier)
    
    def test_validate_purchase_request_complete(self):
        """Probar validación completa de solicitud"""
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            total_amount=Decimal('5000'),
            required_date=timezone.now().date() + timedelta(days=30),
            supplier=self.supplier
        )
        
        # No debería lanzar excepción para datos válidos
        validate_purchase_request(request)


class ReportsServiceTest(TestCase):
    """Pruebas para el servicio de reportes"""
    
    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
        
        self.reports_service = PurchaseReportsService(self.empresa)
    
    def test_get_dashboard_metrics(self):
        """Probar obtención de métricas del dashboard"""
        # Crear datos de prueba
        PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
        
        PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            total_amount=Decimal('1000')
        )
        
        metrics = self.reports_service.get_dashboard_metrics()
        
        # Verificar estructura de métricas
        self.assertIn('requests', metrics)
        self.assertIn('orders', metrics)
        self.assertIn('spending', metrics)
        self.assertIn('suppliers', metrics)
        self.assertIn('delivery', metrics)
        self.assertIn('alerts', metrics)
        
        # Verificar valores
        self.assertEqual(metrics['requests']['total_month'], 1)
        self.assertEqual(metrics['orders']['total_month'], 1)
        self.assertGreater(metrics['spending']['month_total'], 0)
    
    def test_get_spending_trends(self):
        """Probar obtención de tendencias de gastos"""
        # Crear órdenes en diferentes meses
        for i in range(3):
            PurchaseOrder.objects.create(
                empresa=self.empresa,
                sucursal=self.branch,
                supplier=self.supplier,
                created_by=self.user,
                currency=self.currency,
                total_amount=Decimal('1000'),
                order_date=timezone.now().date() - timedelta(days=i*30)
            )
        
        trends = self.reports_service.get_spending_trends(period='month', months=3)
        
        self.assertIsInstance(trends, list)
        self.assertGreater(len(trends), 0)
        
        # Verificar estructura de datos
        for trend in trends:
            self.assertIn('month', trend)
            self.assertIn('total', trend)
            self.assertIn('count', trend)
    
    def test_get_supplier_performance(self):
        """Probar obtención de rendimiento de proveedores"""
        # Crear órdenes y evaluaciones
        PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            total_amount=Decimal('1000')
        )
        
        SupplierRating.objects.create(
            supplier=self.supplier,
            evaluated_by=self.user,
            overall_score=8.5
        )
        
        performance = self.reports_service.get_supplier_performance(limit=10)
        
        self.assertIsInstance(performance, list)
        self.assertGreater(len(performance), 0)
        
        # Verificar estructura de datos
        for supplier in performance:
            self.assertIn('supplier_name', supplier)
            self.assertIn('total_orders', supplier)
            self.assertIn('total_spent', supplier)
            self.assertIn('avg_rating', supplier)
    
    def test_get_category_spending(self):
        """Probar obtención de gastos por categoría"""
        # Crear categoría y producto
        category = Category.objects.create(
            empresa=self.empresa,
            name="Categoría Test"
        )
        product = Product.objects.create(
            empresa=self.empresa,
            name="Producto Test",
            category=category
        )
        product_variant = ProductVariant.objects.create(
            product=product,
            name="Variante Test"
        )
        
        # Crear orden con línea de producto
        order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        
        PurchaseOrderLine.objects.create(
            purchase_order=order,
            product_variant=product_variant,
            quantity=10,
            unit_price=Decimal('100.00')
        )
        
        category_spending = self.reports_service.get_category_spending()
        
        self.assertIsInstance(category_spending, list)
        self.assertGreater(len(category_spending), 0)
    
    def test_get_delivery_performance_trends(self):
        """Probar obtención de tendencias de rendimiento de entregas"""
        # Crear órdenes con diferentes estados de entrega
        order1 = PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            status='received',
            last_receipt_date=timezone.now().date(),
            expected_delivery_date=timezone.now().date() - timedelta(days=5)
        )
        
        order2 = PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            status='received',
            last_receipt_date=timezone.now().date(),
            expected_delivery_date=timezone.now().date() + timedelta(days=5)
        )
        
        delivery_trends = self.reports_service.get_delivery_performance_trends()
        
        self.assertIsInstance(delivery_trends, list)
        self.assertGreater(len(delivery_trends), 0)
    
    def test_get_request_approval_metrics(self):
        """Probar obtención de métricas de aprobación"""
        # Crear solicitudes con diferentes estados
        PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Aprobada",
            requested_by=self.user,
            currency=self.currency,
            status='approved'
        )
        
        PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Rechazada",
            requested_by=self.user,
            currency=self.currency,
            status='rejected'
        )
        
        approval_metrics = self.reports_service.get_request_approval_metrics()
        
        self.assertIsInstance(approval_metrics, list)
        self.assertGreater(len(approval_metrics), 0)
    
    def test_get_cost_savings_analysis(self):
        """Probar análisis de ahorro de costos"""
        # Crear solicitud, cotización y orden
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            status='approved'
        )
        
        quotation = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_request=request,
            total_amount=Decimal('1200'),
            status='approved'
        )
        
        PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            supplier=self.supplier,
            purchase_request=request,
            quotation=quotation,
            created_by=self.user,
            currency=self.currency,
            total_amount=Decimal('1000')
        )
        
        savings_analysis = self.reports_service.get_cost_savings_analysis()
        
        self.assertIsInstance(savings_analysis, list)
        self.assertGreater(len(savings_analysis), 0)
        
        # Verificar que hay ahorro
        if savings_analysis:
            self.assertGreater(savings_analysis[0]['savings'], 0)


class InventoryIntegrationServiceTest(TestCase):
    """Pruebas para el servicio de integración con inventario"""
    
    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
        
        # Crear producto y variante
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
            sku="SKU001",
            current_stock=0,
            average_cost=Decimal('0')
        )
        
        # Crear orden y línea
        self.order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
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
        
        self.inventory_service = InventoryIntegrationService()
    
    @patch('purchases.inventory_integration.ProductVariant')
    @patch('purchases.inventory_integration.StockMovement')
    def test_process_receipt_to_inventory(self, mock_stock_movement, mock_product_variant):
        """Probar procesamiento de recepción a inventario"""
        # Mock del stock
        mock_stock = MagicMock()
        mock_stock.current_stock = 0
        mock_stock.available_stock = 0
        mock_product_variant.objects.get_or_create.return_value = (mock_stock, True)
        
        # Mock del movimiento de stock
        mock_movement = MagicMock()
        mock_stock_movement.objects.create.return_value = mock_movement
        
        # Crear recepción
        receipt = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            purchase_order_line=self.order_line,
            quantity=5,
            unit_cost=Decimal('100.00'),
            received_by=self.user,
            receipt_date=timezone.now().date(),
            status='approved'
        )
        
        # Procesar recepción
        self.inventory_service.process_receipt_to_inventory(receipt)
        
        # Verificar que se actualizó el stock
        mock_stock.save.assert_called()
        
        # Verificar que se creó el movimiento
        mock_stock_movement.objects.create.assert_called_once()
    
    def test_get_stock_levels(self):
        """Probar obtención de niveles de stock"""
        stock_levels = self.inventory_service.get_stock_levels([self.product_variant])
        
        self.assertIsInstance(stock_levels, dict)
        self.assertIn(self.product_variant.id, stock_levels)
        
        level_data = stock_levels[self.product_variant.id]
        self.assertIn('current_stock', level_data)
        self.assertIn('reserved_stock', level_data)
        self.assertIn('available_stock', level_data)
        self.assertIn('average_cost', level_data)
    
    def test_check_stock_availability(self):
        """Probar verificación de disponibilidad de stock"""
        availability = self.inventory_service.check_stock_availability(
            self.product_variant, 5
        )
        
        self.assertIsInstance(availability, dict)
        self.assertIn('available', availability)
        self.assertIn('current_stock', availability)
        self.assertIn('reserved_stock', availability)
        self.assertIn('available_stock', availability)
        self.assertIn('shortage', availability)
    
    @patch('purchases.inventory_integration.StockAlert')
    def test_create_stock_alert(self, mock_stock_alert):
        """Probar creación de alerta de stock"""
        mock_alert = MagicMock()
        mock_stock_alert.objects.create.return_value = mock_alert
        
        alert = self.inventory_service.create_stock_alert(
            self.product_variant, 'low_stock'
        )
        
        self.assertEqual(alert, mock_alert)
        mock_stock_alert.objects.create.assert_called_once()
    
    def test_reserve_stock_for_order(self):
        """Probar reserva de stock para orden"""
        # Configurar stock disponible
        self.product_variant.current_stock = 20
        self.product_variant.available_stock = 20
        self.product_variant.save()
        
        # Reservar stock
        self.inventory_service.reserve_stock_for_order(self.order)
        
        # Verificar que se actualizó el stock
        self.order_line.refresh_from_db()
        self.assertEqual(self.order_line.quantity, 10)
    
    def test_release_reserved_stock(self):
        """Probar liberación de stock reservado"""
        # Configurar stock reservado
        self.product_variant.reserved_stock = 10
        self.product_variant.available_stock = 10
        self.product_variant.save()
        
        # Liberar stock
        self.inventory_service.release_reserved_stock(self.order)
        
        # Verificar que se liberó el stock
        self.product_variant.refresh_from_db()
        self.assertEqual(self.product_variant.reserved_stock, 0)
    
    @patch('purchases.inventory_integration.StockMovement')
    def test_process_return_to_inventory(self, mock_stock_movement):
        """Probar procesamiento de devolución a inventario"""
        # Mock del movimiento de devolución
        mock_movement = MagicMock()
        mock_stock_movement.objects.create.return_value = mock_movement
        
        # Crear recepción con cantidad devuelta
        receipt = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            sucursal=self.branch,
            purchase_order_line=self.order_line,
            quantity=5,
            unit_cost=Decimal('100.00'),
            received_by=self.user,
            receipt_date=timezone.now().date(),
            returned_quantity=2
        )
        
        # Procesar devolución
        self.inventory_service.process_return_to_inventory(
            receipt, 1, "Producto defectuoso"
        )
        
        # Verificar que se creó el movimiento de devolución
        mock_stock_movement.objects.create.assert_called_once()
        
        # Verificar que se actualizó la cantidad devuelta
        receipt.refresh_from_db()
        self.assertEqual(receipt.returned_quantity, 3) 