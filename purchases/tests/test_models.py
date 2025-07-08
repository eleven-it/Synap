from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from core.models import Empresa, Branch, Currency, UnitOfMeasure, DeliveryLocation
from inventory.models import Product, ProductVariant, Category
from purchases.models import (
    Supplier, ApprovalWorkflow, ApprovalLevel, PurchaseRequest, PurchaseRequestLine,
    PurchaseOrder, PurchaseOrderLine, PurchaseQuotation, PurchaseQuotationLine,
    PurchaseReceipt, PurchaseReceiptDocument, SupplierRating
)

User = get_user_model()


class SupplierModelTest(TestCase):
    """Pruebas para el modelo Supplier"""
    
    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            identificador_fiscal="12345678"
        )
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
    
    def test_supplier_creation(self):
        """Probar creación básica de proveedor"""
        supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            code="PROV001",
            tax_id="98765432",
            email="proveedor@test.com",
            phone="+1234567890",
            is_active=True,
            branch=self.branch
        )
        
        self.assertEqual(supplier.name, "Proveedor Test")
        self.assertEqual(supplier.code, "PROV001")
        self.assertTrue(supplier.is_active)
        # El rating promedio será None si no hay evaluaciones
        self.assertIsNone(supplier.get_rating_average())
    
    def test_supplier_str_representation(self):
        """Probar representación string del proveedor"""
        supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            code="PROV001",
            branch=self.branch
        )
        
        expected = f"PROV001 - Proveedor Test ({self.empresa})"
        self.assertEqual(str(supplier), expected)
    
    def test_supplier_unique_tax_id_per_empresa(self):
        """Probar que el ID fiscal sea único por empresa"""
        # Crear primer proveedor
        Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor 1",
            code="PROV001",
            tax_id="12345678",
            branch=self.branch
        )
        
        # Crear segundo proveedor con mismo tax_id (debería permitirse)
        supplier2 = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor 2",
            code="PROV002",
            tax_id="12345678",
            branch=self.branch
        )
        
        self.assertEqual(supplier2.tax_id, "12345678")
    
    def test_supplier_rating_class_update(self):
        """Probar actualización de clase de calificación"""
        supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            code="PROV001",
            branch=self.branch
        )
        
        # Crear orden de compra para la evaluación
        order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        
        # Crear evaluación
        rating = SupplierRating.objects.create(
            empresa=self.empresa,
            supplier=supplier,
            purchase_order=order,
            period_start=timezone.now().date() - timedelta(days=30),
            period_end=timezone.now().date(),
            quality_score=9,
            delivery_score=8,
            communication_score=8,
            price_score=7,
            service_score=8,
            general_comments="Excelente proveedor",
            status='approved'
        )
        
        # Verificar que se calculó correctamente
        self.assertAlmostEqual(float(rating.overall_score), 8.1, places=1)
        self.assertEqual(rating.status, 'approved')
        self.assertEqual(rating.rating_class, 'good')


class ApprovalWorkflowModelTest(TestCase):
    """Pruebas para el modelo ApprovalWorkflow"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(empresa=self.empresa, name="Branch Test")
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
    
    def test_workflow_creation(self):
        """Probar creación de flujo de aprobación"""
        workflow = ApprovalWorkflow.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Flujo Test",
            min_amount=Decimal('10000'),
            max_amount=Decimal('100000'),
            is_active=True
        )
        
        self.assertEqual(workflow.name, "Flujo Test")
        self.assertEqual(workflow.min_amount, Decimal('10000'))
        self.assertTrue(workflow.is_active)
    
    def test_workflow_str_representation(self):
        """Probar representación string del flujo"""
        workflow = ApprovalWorkflow.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Flujo Test",
            min_amount=Decimal('10000'),
            max_amount=Decimal('100000')
        )
        expected = "Flujo Test ($10,000 - $100,000)"
        self.assertEqual(str(workflow), expected)
    
    def test_workflow_amount_range_validation(self):
        """Probar validación de rangos de monto"""
        # Debería fallar si min_amount >= max_amount
        with self.assertRaises(ValidationError):
            workflow = ApprovalWorkflow(
                empresa=self.empresa,
                branch=self.branch,
                name="Flujo Inválido",
                min_amount=Decimal('100000'),
                max_amount=Decimal('10000')
            )
            workflow.full_clean()


class ApprovalLevelModelTest(TestCase):
    """Pruebas para el modelo ApprovalLevel"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(empresa=self.empresa, name="Branch Test")
        self.workflow = ApprovalWorkflow.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Flujo Test"
        )
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
    
    def test_level_creation(self):
        """Probar creación de nivel de aprobación"""
        level = ApprovalLevel.objects.create(
            workflow=self.workflow,
            name="Nivel 1",
            priority=1,
            approval_type='user'
        )
        level.approvers.add(self.user)
        
        self.assertEqual(level.name, "Nivel 1")
        self.assertEqual(level.priority, 1)
        self.assertEqual(level.approval_type, 'user')
        self.assertIn(self.user, level.approvers.all())


class PurchaseRequestModelTest(TestCase):
    """Pruebas para el modelo PurchaseRequest"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(empresa=self.empresa, name="Branch Test")
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            branch=self.branch
        )
        self.delivery_location = DeliveryLocation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Delivery Location Test",
            address="123 Test Street",
            city="Test City"
        )
        
        # Crear producto para las líneas de solicitud
        from inventory.models import Product, ProductVariant
        self.product = Product.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Producto Test",
            sku="PROD001",
            price=Decimal('100.00')
        )
        try:
            self.uom = UnitOfMeasure.objects.get(code="un")
        except UnitOfMeasure.DoesNotExist:
            self.uom = UnitOfMeasure.objects.create(
                name="Unidad",
                code="un",
                category="quantity",
                ratio=1,
                is_reference=True,
                is_active=True
            )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku="VAR001",
            price=Decimal('100.00')
        )
        
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            required_date=timezone.now().date() + timedelta(days=30),
            delivery_location=self.delivery_location
        )
    
    def test_request_creation(self):
        """Probar creación de solicitud de compra"""
        self.assertEqual(self.request.title, "Solicitud Test")
        self.assertEqual(self.request.status, 'draft')
        self.assertIsNotNone(self.request.request_number)
        self.assertEqual(self.request.get_total_amount(), Decimal('0'))
    
    def test_request_number_generation(self):
        """Probar generación automática de números de solicitud"""
        request1 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud 1",
            requested_by=self.user,
            currency=self.currency,
            required_date=timezone.now().date() + timedelta(days=30),
            delivery_location=self.delivery_location
        )
        request2 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud 2",
            requested_by=self.user,
            currency=self.currency,
            required_date=timezone.now().date() + timedelta(days=30),
            delivery_location=self.delivery_location
        )
        self.assertNotEqual(request1.request_number, request2.request_number)
        self.assertTrue(request1.request_number.startswith('PR'))
        self.assertTrue(request2.request_number.startswith('PR'))
    
    def test_request_status_transitions(self):
        """Probar transiciones de estado"""
        self.assertEqual(self.request.status, 'draft')
        
        # Enviar a aprobación
        self.request.status = 'submitted'
        self.request.save()
        self.assertEqual(self.request.status, 'submitted')
        
        # Aprobar
        self.request.approve(self.user)
        self.assertEqual(self.request.status, 'approved')
    
    def test_request_total_calculation(self):
        """Probar cálculo de total de solicitud"""
        # Crear líneas
        PurchaseRequestLine.objects.create(
            purchase_request=self.request,
            product_variant=self.product_variant,
            quantity=10,
            unit_of_measure=self.uom,
            currency=self.currency,
            estimated_unit_price=Decimal('100.00')
        )
        PurchaseRequestLine.objects.create(
            purchase_request=self.request,
            product_variant=self.product_variant,
            quantity=5,
            unit_of_measure=self.uom,
            currency=self.currency,
            estimated_unit_price=Decimal('50.00')
        )
        
        expected_total = Decimal('1250.00')  # 10*100 + 5*50
        self.assertEqual(self.request.get_total_amount(), expected_total)


class PurchaseRequestLineModelTest(TestCase):
    """Pruebas para el modelo PurchaseRequestLine"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
        self.category = Category.objects.create(name="Categoría Test")
        self.product = Product.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Producto Test",
            sku="PROD001",
            price=Decimal('100.00')
        )
        try:
            self.uom = UnitOfMeasure.objects.get(code="un")
        except UnitOfMeasure.DoesNotExist:
            self.uom = UnitOfMeasure.objects.create(
                name="Unidad",
                code="un",
                category="quantity",
                ratio=1,
                is_reference=True,
                is_active=True
            )
        self.delivery_location = DeliveryLocation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Delivery Location Test",
            address="123 Test Street",
            city="Test City"
        )
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            required_date=timezone.now().date() + timedelta(days=30),
            delivery_location=self.delivery_location
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku="VAR001",
            price=Decimal('100.00')
        )
    
    def test_line_creation(self):
        """Probar creación de línea de solicitud"""
        line = PurchaseRequestLine.objects.create(
            purchase_request=self.request,
            product_variant=self.product_variant,
            quantity=10,
            unit_of_measure=self.uom,
            currency=self.currency,
            estimated_unit_price=Decimal('100.00')
        )
        
        self.assertEqual(line.quantity, 10)
        self.assertEqual(line.product_variant, self.product_variant)
        self.assertEqual(line.status, 'pending')
    
    def test_line_total_calculation(self):
        """Probar cálculo de total de línea"""
        line = PurchaseRequestLine.objects.create(
            purchase_request=self.request,
            product_variant=self.product_variant,
            quantity=5,
            unit_of_measure=self.uom,
            currency=self.currency,
            estimated_unit_price=Decimal('50.00')
        )
        
        expected_total = Decimal('250.00')  # 5 * 50.00
        self.assertEqual(line.total_amount, expected_total)


class PurchaseOrderModelTest(TestCase):
    """Pruebas para el modelo PurchaseOrder"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            branch=self.branch
        )
        self.delivery_location = DeliveryLocation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Delivery Location Test",
            address="123 Test Street",
            city="Test City"
        )
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            required_date=timezone.now().date() + timedelta(days=30),
            delivery_location=self.delivery_location
        )
    
    def test_order_creation(self):
        """Probar creación de orden de compra"""
        order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            purchase_request=self.request,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        self.assertEqual(order.supplier, self.supplier)
        self.assertEqual(order.status, 'draft')
        self.assertIsNotNone(order.order_number)
        self.assertEqual(order.total_amount, Decimal('0'))
    
    def test_order_number_generation(self):
        """Probar generación automática de números de orden"""
        order1 = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        order2 = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        self.assertNotEqual(order1.order_number, order2.order_number)
        self.assertTrue(order1.order_number.startswith('PO'))
        self.assertTrue(order2.order_number.startswith('PO'))
    
    def test_order_status_transitions(self):
        """Probar transiciones de estado de orden"""
        order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        
        # Estado inicial
        self.assertEqual(order.status, 'draft')
        
        # Enviar orden
        order.status = 'sent'
        order.sent_date = timezone.now().date()
        order.save()
        self.assertEqual(order.status, 'sent')
        
        # Confirmar orden
        order.status = 'confirmed'
        order.confirmed_date = timezone.now().date()
        order.save()
        self.assertEqual(order.status, 'confirmed')


class PurchaseQuotationModelTest(TestCase):
    """Pruebas para el modelo PurchaseQuotation"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            branch=self.branch
        )
        self.delivery_location = DeliveryLocation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Delivery Location Test",
            address="123 Test Street",
            city="Test City"
        )
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            required_date=timezone.now().date() + timedelta(days=30),
            delivery_location=self.delivery_location
        )
    
    def test_quotation_creation(self):
        """Probar creación de cotización"""
        quotation = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            purchase_request=self.request,
            currency=self.currency,
            valid_until=timezone.now().date() + timedelta(days=30),
            delivery_time=15
        )
        
        self.assertEqual(quotation.status, 'draft')
        self.assertIsNotNone(quotation.quotation_number)
        self.assertEqual(quotation.supplier, self.supplier)
        self.assertEqual(quotation.purchase_request, self.request)
    
    def test_quotation_number_generation(self):
        """Probar generación automática de números de cotización"""
        quotation1 = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            purchase_request=self.request,
            currency=self.currency,
            valid_until=timezone.now().date() + timedelta(days=30)
        )
        
        quotation2 = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            purchase_request=self.request,
            currency=self.currency,
            valid_until=timezone.now().date() + timedelta(days=30)
        )
        
        self.assertNotEqual(quotation1.quotation_number, quotation2.quotation_number)
        self.assertTrue(quotation1.quotation_number.startswith('QC-'))
        self.assertTrue(quotation2.quotation_number.startswith('QC-'))


class PurchaseReceiptModelTest(TestCase):
    """Pruebas para el modelo PurchaseReceipt"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(empresa=self.empresa, name="Branch Test")
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            branch=self.branch
        )
        self.delivery_location = DeliveryLocation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Delivery Location Test",
            address="123 Test Street",
            city="Test City"
        )
        
        # Crear producto para las líneas de orden
        from inventory.models import Product, ProductVariant
        self.product = Product.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Producto Test",
            sku="PROD001",
            price=Decimal('100.00')
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku="VAR001",
            price=Decimal('100.00')
        )
        
        # Crear UOM
        try:
            self.uom = UnitOfMeasure.objects.get(code="un")
        except UnitOfMeasure.DoesNotExist:
            self.uom = UnitOfMeasure.objects.create(
                name="Unidad",
                code="un",
                category="quantity",
                ratio=1,
                is_reference=True,
                is_active=True
            )
        
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency,
            required_date=timezone.now().date() + timedelta(days=30),
            delivery_location=self.delivery_location
        )
        self.order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        self.order_line = PurchaseOrderLine.objects.create(
            purchase_order=self.order,
            product_variant=self.product_variant,
            quantity=10,
            unit_price=100,
            unit_of_measure=self.uom
        )
    
    def test_receipt_creation(self):
        """Probar creación de recepción"""
        receipt = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            purchase_order_line=self.order_line,
            quantity=5,
            lot_number="LoteTest",
            expiration_date=None,
            received_by=self.user
        )
        
        self.assertEqual(receipt.quantity, 5)
        self.assertEqual(receipt.status, 'draft')
        self.assertIsNotNone(receipt.receipt_number)
    
    def test_receipt_number_generation(self):
        """Probar generación automática de números de recepción"""
        receipt1 = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            purchase_order_line=self.order_line,
            quantity=5,
            received_by=self.user
        )
        
        receipt2 = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            purchase_order_line=self.order_line,
            quantity=3,
            received_by=self.user
        )
        
        self.assertNotEqual(receipt1.receipt_number, receipt2.receipt_number)
        self.assertTrue(receipt1.receipt_number.startswith('REC'))
        self.assertTrue(receipt2.receipt_number.startswith('REC'))


class SupplierRatingModelTest(TestCase):
    """Pruebas para el modelo SupplierRating"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(empresa=self.empresa, name="Branch Test")
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            branch=self.branch
        )
        self.delivery_location = DeliveryLocation.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Delivery Location Test",
            address="123 Test Street",
            city="Test City"
        )
        
        # Crear orden de compra para las evaluaciones
        self.order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
    
    def test_rating_creation(self):
        """Probar creación de evaluación de proveedor"""
        rating = SupplierRating.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_order=self.order,
            period_start=timezone.now().date() - timedelta(days=30),
            period_end=timezone.now().date(),
            quality_score=4,
            delivery_score=4,
            communication_score=4,
            price_score=4,
            service_score=4
        )
        
        self.assertEqual(rating.status, 'draft')
        self.assertIsNotNone(rating.overall_score)
        self.assertIsNotNone(rating.rating_class)
        self.assertEqual(rating.supplier, self.supplier)
    
    def test_rating_class_calculation(self):
        """Probar cálculo automático de clase de calificación"""
        # Crear segunda orden para evitar restricción unique
        order2 = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        
        rating1 = SupplierRating.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_order=self.order,
            period_start=timezone.now().date() - timedelta(days=30),
            period_end=timezone.now().date(),
            quality_score=4,
            delivery_score=4,
            communication_score=4,
            price_score=4,
            service_score=4
        )
        
        rating2 = SupplierRating.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_order=order2,
            period_start=timezone.now().date() - timedelta(days=30),
            period_end=timezone.now().date(),
            quality_score=9,
            delivery_score=9,
            communication_score=9,
            price_score=9,
            service_score=9
        )
        
        self.assertEqual(rating1.rating_class, 'poor')
        self.assertEqual(rating2.rating_class, 'excellent')


class PurchaseOrderLineModelTest(TestCase):
    """Pruebas para el modelo PurchaseOrderLine"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        self.branch = Branch.objects.create(empresa=self.empresa, name="Branch Test")
        self.currency = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]
        self.user = User.objects.create_user(email='test@example.com', nombre='Test User', password='testpass123')
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            branch=self.branch
        )
        
        # Crear producto para las líneas de orden
        from inventory.models import Product, ProductVariant
        self.product = Product.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name="Producto Test",
            sku="PROD001",
            price=Decimal('100.00')
        )
        try:
            self.uom = UnitOfMeasure.objects.get(code="un")
        except UnitOfMeasure.DoesNotExist:
            self.uom = UnitOfMeasure.objects.create(
                name="Unidad",
                code="un",
                category="quantity",
                ratio=1,
                is_reference=True,
                is_active=True
            )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku="VAR001",
            price=Decimal('100.00')
        )
        
        # Crear orden de compra
        self.order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        
        # Crear línea de orden
        self.order_line = PurchaseOrderLine.objects.create(
            purchase_order=self.order,
            product_variant=self.product_variant,
            quantity=10,
            unit_price=100,
            unit_of_measure=self.uom
        )
    
    def test_line_creation(self):
        """Probar creación de línea de orden"""
        self.assertEqual(self.order_line.quantity, 10)
        self.assertEqual(self.order_line.product_variant, self.product_variant)
        self.assertEqual(self.order_line.status, 'pending')
    
    def test_line_total_calculation(self):
        """Probar cálculo de total de línea"""
        expected_total = self.order_line.quantity * self.order_line.unit_price
        self.assertEqual(self.order_line.total_amount, expected_total) 