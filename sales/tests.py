from django.test import TestCase, Client as DjangoClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

from .models import (
    SalesOrder, SalesOrderLine, Client, PriceList, PaymentTerm,
    SalesOrderStates, SalesOrderLineStates, ApprovalLog
)
from .utils import SalesOrderWorkflow, SalesOrderCalculator, SalesOrderValidator
from inventory.models import Product, ProductVariant
from core.models import Branch, Empresa, Rol, Permiso

User = get_user_model()


class SalesOrderModelTest(TestCase):
    """Tests para el modelo SalesOrder"""

    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            email='test@seller.com',
            nombre='Test Seller',
            password='testpass123'
        )
        
        # Asignar rol de vendedor
        rol_vendedor, created = Rol.objects.get_or_create(
            nombre='Vendedor',
            defaults={
                'descripcion': 'Gestión de ventas y clientes',
                'activo': True
            }
        )
        
        # Crear permisos de ventas si no existen
        permisos_ventas = [
            ('ventas.ver', 'Ver ventas'),
            ('ventas.crear', 'Crear ventas'),
            ('ventas.editar', 'Editar ventas'),
        ]
        
        for codigo, nombre in permisos_ventas:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'modulo': 'ventas',
                    'activo': True
                }
            )
            rol_vendedor.permisos.add(permiso)
        
        self.user.roles.add(rol_vendedor)
        
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            identificador_fiscal='12345678'
        )
        self.branch = Branch.objects.create(
            name='Test Branch',
            empresa=self.empresa
        )
        
        # Crear producto y variante
        self.product = Product.objects.create(
            name='Test Product',
            sku='TP001',
            empresa=self.empresa,
            branch=self.branch,
            price=Decimal('100.00'),
            type='stockable'
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku='TV001',
            price=Decimal('100.00')
        )
        
        # Crear cliente
        self.client_obj = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            type='company',
            credit_limit=Decimal('10000.00')
        )
        
        # Crear lista de precios
        self.price_list = PriceList.objects.create(
            name='Test Price List',
            currency='USD'
        )
        
        # Crear condiciones de pago
        self.payment_term = PaymentTerm.objects.create(
            name='Test Payment Term'
        )

    def test_sales_order_creation(self):
        """Test creación de pedido de venta"""
        order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        self.assertIsNotNone(order.number)
        self.assertEqual(order.state, SalesOrderStates.DRAFT)
        self.assertEqual(order.total, Decimal('0.00'))

    def test_sales_order_line_creation(self):
        """Test creación de línea de pedido"""
        order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        line = SalesOrderLine.objects.create(
            sales_order=order,
            product_variant=self.product_variant,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )
        
        self.assertEqual(line.subtotal, Decimal('200.00'))
        self.assertEqual(line.state, SalesOrderLineStates.DRAFT)

    def test_order_number_generation(self):
        """Test generación automática de número de pedido"""
        order1 = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        order2 = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        self.assertNotEqual(order1.number, order2.number)
        self.assertTrue(order1.number.startswith('SO-'))


class SalesOrderWorkflowTest(TestCase):
    """Tests para el workflow de pedidos de venta"""

    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            email='test@seller.com',
            nombre='Test Seller',
            password='testpass123'
        )
        
        # Asignar rol de vendedor
        rol_vendedor, created = Rol.objects.get_or_create(
            nombre='Vendedor',
            defaults={
                'descripcion': 'Gestión de ventas y clientes',
                'activo': True
            }
        )
        
        # Crear permisos de ventas si no existen
        permisos_ventas = [
            ('ventas.ver', 'Ver ventas'),
            ('ventas.crear', 'Crear ventas'),
            ('ventas.editar', 'Editar ventas'),
        ]
        
        for codigo, nombre in permisos_ventas:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'modulo': 'ventas',
                    'activo': True
                }
            )
            rol_vendedor.permisos.add(permiso)
        
        self.user.roles.add(rol_vendedor)
        
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            identificador_fiscal='12345678'
        )
        self.branch = Branch.objects.create(
            name='Test Branch',
            empresa=self.empresa
        )
        
        # Crear producto y variante
        self.product = Product.objects.create(
            name='Test Product',
            sku='TP001',
            empresa=self.empresa,
            branch=self.branch,
            price=Decimal('100.00'),
            type='stockable'
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku='TV001',
            price=Decimal('100.00')
        )
        
        # Crear cliente
        self.client_obj = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            type='company',
            credit_limit=Decimal('10000.00')
        )
        
        # Crear lista de precios
        self.price_list = PriceList.objects.create(
            name='Test Price List',
            currency='USD'
        )
        
        # Crear condiciones de pago
        self.payment_term = PaymentTerm.objects.create(
            name='Test Payment Term'
        )
        
        # Crear pedido con línea
        self.order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        # Agregar línea al pedido
        SalesOrderLine.objects.create(
            sales_order=self.order,
            product_variant=self.product_variant,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )

    def test_workflow_transitions(self):
        """Test transiciones válidas del workflow"""
        # Draft -> Quotation Sent
        self.order.send_quotation(self.user, "Sending quotation")
        self.assertEqual(self.order.state, SalesOrderStates.QUOTATION_SENT)
        
        # Quotation Sent -> Confirmed
        self.order.confirm_order(self.user, "Client confirmed")
        self.assertEqual(self.order.state, SalesOrderStates.CONFIRMED)
        
        # Confirmed -> In Process
        self.order.start_processing(self.user, "Starting processing")
        self.assertEqual(self.order.state, SalesOrderStates.IN_PROCESS)

    def test_invalid_transitions(self):
        """Test transiciones inválidas"""
        # Intentar transición inválida
        with self.assertRaises(ValidationError):
            self.order.transition_to(SalesOrderStates.INVOICED, self.user, "Invalid transition")

    def test_required_reason(self):
        """Test que el motivo sea obligatorio"""
        with self.assertRaises(ValidationError):
            self.order.transition_to(SalesOrderStates.QUOTATION_SENT, self.user, None)

    def test_cancel_order(self):
        """Test cancelación de pedido"""
        self.order.cancel_order(self.user, "Client cancelled")
        self.assertEqual(self.order.state, SalesOrderStates.CANCELLED)

    def test_approval_log_creation(self):
        """Test creación de logs de aprobación"""
        self.order.send_quotation(self.user, "Test reason")
        
        log = ApprovalLog.objects.filter(sales_order=self.order).latest('action_date')
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'state_change')


class SalesOrderCalculatorTest(TestCase):
    """Tests para cálculos de pedidos de venta"""

    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            email='test@seller.com',
            nombre='Test Seller',
            password='testpass123'
        )
        
        # Asignar rol de vendedor
        rol_vendedor, created = Rol.objects.get_or_create(
            nombre='Vendedor',
            defaults={
                'descripcion': 'Gestión de ventas y clientes',
                'activo': True
            }
        )
        
        # Crear permisos de ventas si no existen
        permisos_ventas = [
            ('ventas.ver', 'Ver ventas'),
            ('ventas.crear', 'Crear ventas'),
            ('ventas.editar', 'Editar ventas'),
        ]
        
        for codigo, nombre in permisos_ventas:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'modulo': 'ventas',
                    'activo': True
                }
            )
            rol_vendedor.permisos.add(permiso)
        
        self.user.roles.add(rol_vendedor)
        
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            identificador_fiscal='12345678'
        )
        self.branch = Branch.objects.create(
            name='Test Branch',
            empresa=self.empresa
        )
        
        # Crear producto y variante
        self.product = Product.objects.create(
            name='Test Product',
            sku='TP001',
            empresa=self.empresa,
            branch=self.branch,
            price=Decimal('100.00'),
            type='stockable'
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku='TV001',
            price=Decimal('100.00')
        )
        
        # Crear cliente
        self.client_obj = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            type='company',
            credit_limit=Decimal('10000.00')
        )
        
        # Crear lista de precios
        self.price_list = PriceList.objects.create(
            name='Test Price List',
            currency='USD'
        )
        
        # Crear condiciones de pago
        self.payment_term = PaymentTerm.objects.create(
            name='Test Payment Term'
        )
        
        # Crear pedido con línea
        self.order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        # Agregar línea al pedido
        self.line = SalesOrderLine.objects.create(
            sales_order=self.order,
            product_variant=self.product_variant,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )

    def test_line_subtotal_calculation(self):
        """Test cálculo de subtotal de línea"""
        self.assertEqual(self.line.subtotal, Decimal('200.00'))
        
        # Con descuento
        self.line.discount = Decimal('10.00')
        self.line.save()
        self.assertEqual(self.line.subtotal, Decimal('180.00'))

    def test_order_totals_calculation(self):
        """Test cálculo de totales del pedido"""
        self.order.recalculate_totals()
        self.assertEqual(self.order.total, Decimal('200.00'))

    def test_delivery_progress_calculation(self):
        """Test cálculo de progreso de entrega"""
        progress = self.order.get_delivery_progress()
        self.assertEqual(progress, 0)
        
        # Marcar línea como entregada
        self.line.state = SalesOrderLineStates.DELIVERED
        self.line.save()
        
        progress = self.order.get_delivery_progress()
        self.assertEqual(progress, 100)

    def test_payment_progress_calculation(self):
        """Test cálculo de progreso de pago"""
        # Estado draft
        progress = self.order.get_payment_progress()
        self.assertEqual(progress, 0)
        
        # Estado confirmed
        self.order.state = SalesOrderStates.CONFIRMED
        self.order.save()
        progress = self.order.get_payment_progress()
        self.assertEqual(progress, 25)


class SalesOrderValidatorTest(TestCase):
    """Tests para validaciones de pedidos de venta"""

    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            email='test@seller.com',
            nombre='Test Seller',
            password='testpass123'
        )
        
        # Asignar rol de vendedor
        rol_vendedor, created = Rol.objects.get_or_create(
            nombre='Vendedor',
            defaults={
                'descripcion': 'Gestión de ventas y clientes',
                'activo': True
            }
        )
        
        # Crear permisos de ventas si no existen
        permisos_ventas = [
            ('ventas.ver', 'Ver ventas'),
            ('ventas.crear', 'Crear ventas'),
            ('ventas.editar', 'Editar ventas'),
        ]
        
        for codigo, nombre in permisos_ventas:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'modulo': 'ventas',
                    'activo': True
                }
            )
            rol_vendedor.permisos.add(permiso)
        
        self.user.roles.add(rol_vendedor)
        
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            identificador_fiscal='12345678'
        )
        self.branch = Branch.objects.create(
            name='Test Branch',
            empresa=self.empresa
        )
        
        # Crear producto y variante
        self.product = Product.objects.create(
            name='Test Product',
            sku='TP001',
            empresa=self.empresa,
            branch=self.branch,
            price=Decimal('100.00'),
            type='stockable'
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku='TV001',
            price=Decimal('100.00')
        )
        
        # Crear cliente
        self.client_obj = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            type='company',
            credit_limit=Decimal('10000.00')
        )
        
        # Crear lista de precios
        self.price_list = PriceList.objects.create(
            name='Test Price List',
            currency='USD'
        )
        
        # Crear condiciones de pago
        self.payment_term = PaymentTerm.objects.create(
            name='Test Payment Term'
        )
        
        # Crear pedido con línea
        self.order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        # Agregar línea al pedido
        self.line = SalesOrderLine.objects.create(
            sales_order=self.order,
            product_variant=self.product_variant,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )

    def test_state_transition_validation(self):
        """Test validación de transiciones de estado"""
        # Transición válida
        self.assertTrue(self.order.can_transition_to(SalesOrderStates.QUOTATION_SENT))
        
        # Transición inválida
        self.assertFalse(self.order.can_transition_to(SalesOrderStates.INVOICED))

    def test_order_confirmation_validation(self):
        """Test validación para confirmación de pedido"""
        self.order.send_quotation(self.user, "Sending quotation")
        self.assertTrue(self.order.can_transition_to(SalesOrderStates.CONFIRMED))

    def test_delivery_validation(self):
        """Test validación para entrega"""
        self.order.send_quotation(self.user, "Sending quotation")
        self.order.confirm_order(self.user, "Client confirmed")
        self.order.start_processing(self.user, "Starting processing")
        self.assertTrue(self.order.can_create_delivery())

    def test_invoicing_validation(self):
        """Test validación para facturación"""
        self.order.send_quotation(self.user, "Sending quotation")
        self.order.confirm_order(self.user, "Client confirmed")
        self.order.start_processing(self.user, "Starting processing")
        self.order.mark_ready_to_deliver(self.user, "Ready to deliver")
        self.order.mark_delivered(self.user, "Delivered")
        self.assertTrue(self.order.can_create_invoice())


class SalesOrderViewTest(TestCase):
    """Tests para vistas de pedidos de venta"""

    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            email='test@seller.com',
            nombre='Test Seller',
            password='testpass123'
        )
        
        # Asignar rol de vendedor
        rol_vendedor, created = Rol.objects.get_or_create(
            nombre='Vendedor',
            defaults={
                'descripcion': 'Gestión de ventas y clientes',
                'activo': True
            }
        )
        
        # Crear permisos de ventas si no existen
        permisos_ventas = [
            ('ventas.ver', 'Ver ventas'),
            ('ventas.crear', 'Crear ventas'),
            ('ventas.editar', 'Editar ventas'),
        ]
        
        for codigo, nombre in permisos_ventas:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'modulo': 'ventas',
                    'activo': True
                }
            )
            rol_vendedor.permisos.add(permiso)
        
        self.user.roles.add(rol_vendedor)
        
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            identificador_fiscal='12345678'
        )
        self.branch = Branch.objects.create(
            name='Test Branch',
            empresa=self.empresa
        )
        
        # Crear producto y variante
        self.product = Product.objects.create(
            name='Test Product',
            sku='TP001',
            empresa=self.empresa,
            branch=self.branch,
            price=Decimal('100.00'),
            type='stockable'
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku='TV001',
            price=Decimal('100.00')
        )
        
        # Crear cliente
        self.client_obj = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            type='company',
            credit_limit=Decimal('10000.00')
        )
        
        # Crear lista de precios
        self.price_list = PriceList.objects.create(
            name='Test Price List',
            currency='USD'
        )
        
        # Crear condiciones de pago
        self.payment_term = PaymentTerm.objects.create(
            name='Test Payment Term'
        )
        
        # Crear pedido con línea
        self.order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        # Agregar línea al pedido
        self.line = SalesOrderLine.objects.create(
            sales_order=self.order,
            product_variant=self.product_variant,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )
        
        # Crear cliente HTTP
        self.client = DjangoClient()
        self.client.login(email='test@seller.com', password='testpass123')

    def test_sales_order_list_view(self):
        """Test vista de lista de pedidos"""
        response = self.client.get(reverse('sales:sales_order_list'))
        self.assertEqual(response.status_code, 200)

    def test_sales_order_list_filtering(self):
        """Test filtrado en lista de pedidos"""
        response = self.client.get(reverse('sales:sales_order_list'), {
            'state': 'draft'
        })
        self.assertEqual(response.status_code, 200)

    def test_sales_order_detail_view(self):
        """Test vista de detalle de pedido"""
        response = self.client.get(reverse('sales:sales_order_detail', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)

    def test_sales_order_detail_post_action(self):
        """Test acciones POST en vista de detalle"""
        response = self.client.post(reverse('sales:sales_order_detail', args=[self.order.id]), {
            'action': 'send_quotation',
            'reason': 'Sending quotation to client'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after action
        
        # Verificar que el estado cambió
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, SalesOrderStates.QUOTATION_SENT)

    def test_sales_order_detail_post_invalid_action(self):
        """Test acción POST inválida"""
        response = self.client.post(reverse('sales:sales_order_detail', args=[self.order.id]), {
            'action': 'invalid_action',
            'reason': 'Invalid action'
        })
        self.assertEqual(response.status_code, 200)  # Stay on page with error

    def test_sales_order_detail_post_no_reason(self):
        """Test acción POST sin motivo"""
        response = self.client.post(reverse('sales:sales_order_detail', args=[self.order.id]), {
            'action': 'send_quotation',
            'reason': ''
        })
        self.assertEqual(response.status_code, 200)  # Stay on page with error


class SalesOrderIntegrationTest(TestCase):
    """Tests de integración para flujo completo"""

    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario
        self.user = User.objects.create_user(
            email='test@seller.com',
            nombre='Test Seller',
            password='testpass123'
        )
        
        # Asignar rol de vendedor
        rol_vendedor, created = Rol.objects.get_or_create(
            nombre='Vendedor',
            defaults={
                'descripcion': 'Gestión de ventas y clientes',
                'activo': True
            }
        )
        
        # Crear permisos de ventas si no existen
        permisos_ventas = [
            ('ventas.ver', 'Ver ventas'),
            ('ventas.crear', 'Crear ventas'),
            ('ventas.editar', 'Editar ventas'),
        ]
        
        for codigo, nombre in permisos_ventas:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'modulo': 'ventas',
                    'activo': True
                }
            )
            rol_vendedor.permisos.add(permiso)
        
        self.user.roles.add(rol_vendedor)
        
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            identificador_fiscal='12345678'
        )
        self.branch = Branch.objects.create(
            name='Test Branch',
            empresa=self.empresa
        )
        
        # Crear producto y variante
        self.product = Product.objects.create(
            name='Test Product',
            sku='TP001',
            empresa=self.empresa,
            branch=self.branch,
            price=Decimal('100.00'),
            type='stockable'
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            sku='TV001',
            price=Decimal('100.00')
        )
        
        # Crear cliente
        self.client_obj = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            type='company',
            credit_limit=Decimal('10000.00')
        )
        
        # Crear lista de precios
        self.price_list = PriceList.objects.create(
            name='Test Price List',
            currency='USD'
        )
        
        # Crear condiciones de pago
        self.payment_term = PaymentTerm.objects.create(
            name='Test Payment Term'
        )
        
        # Crear pedido con línea
        self.order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user
        )
        
        # Agregar línea al pedido
        self.line = SalesOrderLine.objects.create(
            sales_order=self.order,
            product_variant=self.product_variant,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00')
        )

    def test_complete_workflow_integration(self):
        """Test flujo completo de pedido de venta"""
        # 1. Crear pedido (ya hecho en setUp)
        self.assertEqual(self.order.state, SalesOrderStates.DRAFT)
        
        # 2. Enviar cotización
        self.order.send_quotation(self.user, "Sending quotation")
        self.assertEqual(self.order.state, SalesOrderStates.QUOTATION_SENT)
        
        # 3. Confirmar pedido
        self.order.confirm_order(self.user, "Client confirmed")
        self.assertEqual(self.order.state, SalesOrderStates.CONFIRMED)
        
        # 4. Iniciar procesamiento
        self.order.start_processing(self.user, "Starting processing")
        self.assertEqual(self.order.state, SalesOrderStates.IN_PROCESS)
        
        # 5. Marcar listo para entregar
        self.order.mark_ready_to_deliver(self.user, "Ready to deliver")
        self.assertEqual(self.order.state, SalesOrderStates.READY_TO_DELIVER)
        
        # 6. Marcar entregado
        self.order.mark_delivered(self.user, "Delivered")
        self.assertEqual(self.order.state, SalesOrderStates.DELIVERED)
        
        # 7. Marcar facturado
        self.order.mark_invoiced(self.user, "Invoiced")
        self.assertEqual(self.order.state, SalesOrderStates.INVOICED)
        
        # 8. Marcar pagado
        self.order.mark_paid(self.user, "Paid")
        self.assertEqual(self.order.state, SalesOrderStates.PAID)
        
        # 9. Marcar completado
        self.order.mark_completed(self.user, "Completed")
        self.assertEqual(self.order.state, SalesOrderStates.COMPLETED)

    def test_workflow_with_ui_actions(self):
        """Test workflow usando acciones de UI"""
        # Simular acción de UI para enviar cotización
        self.order.send_quotation(self.user, "Sending quotation")
        
        # Verificar que el estado cambió
        self.assertEqual(self.order.state, SalesOrderStates.QUOTATION_SENT)
        
        # Verificar que se creó el log
        log = ApprovalLog.objects.filter(sales_order=self.order).latest('action_date')
        self.assertIsNotNone(log)
        self.assertEqual(log.action, 'state_change')
