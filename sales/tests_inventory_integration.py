from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

from .models import (
    SalesOrder, SalesOrderLine, Client, PriceList, PaymentTerm,
    SalesOrderStates, SalesOrderLineStates, ApprovalLog
)
from .services import SalesInventoryService, SalesInventoryValidator
from inventory.models import (
    Product, ProductVariant, StockQuant, StockReservation, 
    StockMove, Location, Warehouse
)
from core.models import Branch, Empresa

User = get_user_model()


class SalesInventoryIntegrationTest(TestCase):
    """Tests para la integración entre ventas e inventario"""

    def setUp(self):
        """Configurar datos de prueba"""
        # Crear empresa y sucursal
        self.empresa = Empresa.objects.create(
            nombre='Test Company',
            identificador_fiscal='12345678'
        )
        self.branch = Branch.objects.create(
            name='Test Branch',
            empresa=self.empresa
        )
        
        # Crear usuario
        self.user = User.objects.create_user(
            email='test@seller.com',
            nombre='Test Seller',
            password='testpass123'
        )
        
        # Crear cliente
        self.client_obj = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            type='company',
            credit_limit=Decimal('10000.00')
        )
        
        # Crear términos de pago y lista de precios
        self.payment_term = PaymentTerm.objects.create(
            name='Net 30'
        )
        self.price_list = PriceList.objects.create(
            name='Standard',
            currency='USD'
        )
        
        # Crear almacén y ubicación
        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            empresa=self.empresa,
            branch=self.branch
        )
        self.location = Location.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            name='Storage Area A',
            location_type='internal',
            warehouse=self.warehouse,
            is_active=True,
            allow_operations=True
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
        
        # Crear stock inicial
        self.stock_quant = StockQuant.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            product=self.product,
            location=self.location,
            quantity=Decimal('50.00'),
            reserved_quantity=Decimal('0.00')
        )
        
        # Crear pedido de venta
        self.order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.client_obj,
            branch=self.branch,
            payment_term=self.payment_term,
            price_list=self.price_list,
            seller=self.user,
            state=SalesOrderStates.DRAFT
        )
        
        # Crear línea de pedido
        self.order_line = SalesOrderLine.objects.create(
            sales_order=self.order,
            product_variant=self.product_variant,
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            discount=Decimal('0.00'),
            state=SalesOrderLineStates.DRAFT
        )

    def test_stock_availability_validation(self):
        """Test validación de disponibilidad de stock"""
        # Validar stock disponible
        validation = SalesInventoryService.validate_stock_availability(self.order)
        
        # Debe tener stock suficiente (50 disponible, 10 solicitado)
        self.assertEqual(len(validation['errors']), 0)
        self.assertEqual(len(validation['warnings']), 0)
        
        # Modificar cantidad a más del stock disponible
        self.order_line.quantity = Decimal('60.00')
        self.order_line.save()
        
        validation = SalesInventoryService.validate_stock_availability(self.order)
        self.assertEqual(len(validation['errors']), 1)
        self.assertIn('Stock insuficiente', validation['errors'][0])

    def test_stock_reservation_on_confirmation(self):
        """Test reserva de stock al confirmar pedido"""
        # Confirmar pedido
        self.order.confirm_order(self.user, 'Testing stock reservation')
        
        # Verificar que se crearon reservas
        reservations = StockReservation.objects.filter(
            reserved_for=f"SO-{self.order.number}",
            status='active'
        )
        self.assertEqual(reservations.count(), 1)
        
        # Verificar cantidad reservada
        reservation = reservations.first()
        self.assertEqual(reservation.quantity, Decimal('10.00'))
        self.assertEqual(reservation.product, self.product)
        
        # Verificar que se actualizó StockQuant
        self.stock_quant.refresh_from_db()
        self.assertEqual(self.stock_quant.reserved_quantity, Decimal('10.00'))
        self.assertEqual(self.stock_quant.available_quantity, Decimal('40.00'))

    def test_stock_release_on_cancellation(self):
        """Test liberación de stock al cancelar pedido"""
        # Confirmar pedido para crear reservas
        self.order.confirm_order(self.user, 'Testing stock release')
        
        # Verificar reservas creadas
        self.assertEqual(
            StockReservation.objects.filter(
                reserved_for=f"SO-{self.order.number}",
                status='active'
            ).count(), 1
        )
        
        # Cancelar pedido
        self.order.cancel_order(self.user, 'Testing stock release')
        
        # Verificar que se liberaron las reservas
        active_reservations = StockReservation.objects.filter(
            reserved_for=f"SO-{self.order.number}",
            status='active'
        )
        self.assertEqual(active_reservations.count(), 0)
        
        # Verificar que se actualizó StockQuant
        self.stock_quant.refresh_from_db()
        self.assertEqual(self.stock_quant.reserved_quantity, Decimal('0.00'))
        self.assertEqual(self.stock_quant.available_quantity, Decimal('50.00'))

    def test_stock_moves_on_delivery(self):
        """Test creación de movimientos de stock al entregar"""
        # Confirmar pedido
        self.order.confirm_order(self.user, 'Testing stock moves')
        # Iniciar procesamiento
        self.order.start_processing(self.user, 'Start processing')
        # Marcar como listo para entregar
        self.order.mark_ready_to_deliver(self.user, 'Ready to deliver')
        # Entregar pedido
        self.order.mark_delivered(self.user, 'Testing stock moves')
        # Verificar que se crearon movimientos de stock
        stock_moves = StockMove.objects.filter(
            reference=f"SO-{self.order.number}",
            origin='sales_delivery'
        )
        self.assertEqual(stock_moves.count(), 1)
        # Verificar detalles del movimiento
        stock_move = stock_moves.first()
        self.assertEqual(stock_move.quantity, Decimal('10.00'))
        self.assertEqual(stock_move.move_type, 'outgoing')
        self.assertEqual(stock_move.state, 'confirmed')
        self.assertEqual(stock_move.from_location, self.location)
        # Verificar que se actualizó StockQuant
        self.stock_quant.refresh_from_db()
        self.assertEqual(self.stock_quant.quantity, Decimal('40.00'))
        self.assertEqual(self.stock_quant.reserved_quantity, Decimal('0.00'))

    def test_stock_validator_functions(self):
        """Test funciones del validador de stock"""
        # Modificar cantidad a más del stock disponible
        self.order_line.quantity = Decimal('60.00')
        self.order_line.save()
        # Verificar que no se puede confirmar sin stock
        self.assertFalse(SalesInventoryValidator.can_confirm_order(self.order))
        # Agregar stock suficiente
        self.order_line.quantity = Decimal('10.00')
        self.order_line.save()
        self.stock_quant.quantity = Decimal('100.00')
        self.stock_quant.save()
        # Ahora debe poder confirmarse
        self.assertTrue(SalesInventoryValidator.can_confirm_order(self.order))
        # Confirmar pedido
        self.order.confirm_order(self.user, 'Testing validator')
        # Iniciar procesamiento
        self.order.start_processing(self.user, 'Start processing')
        # Marcar como listo para entregar
        self.order.mark_ready_to_deliver(self.user, 'Ready to deliver')
        # Obtener resumen de stock
        summary = SalesInventoryValidator.get_stock_summary(self.order)
        self.assertEqual(summary['order_number'], self.order.number)
        self.assertTrue(summary['can_confirm'])
        self.assertTrue(summary['can_deliver'])

    def test_multiple_line_stock_management(self):
        """Test gestión de stock con múltiples líneas"""
        # Crear segundo producto
        product2 = Product.objects.create(
            name='Test Product 2',
            sku='TP002',
            empresa=self.empresa,
            branch=self.branch,
            price=Decimal('50.00'),
            type='stockable'
        )
        variant2 = ProductVariant.objects.create(
            product=product2,
            sku='TV002',
            price=Decimal('50.00')
        )
        
        # Crear stock para segundo producto
        StockQuant.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            product=product2,
            location=self.location,
            quantity=Decimal('20.00'),
            reserved_quantity=Decimal('0.00')
        )
        
        # Agregar segunda línea al pedido
        SalesOrderLine.objects.create(
            sales_order=self.order,
            product_variant=variant2,
            quantity=Decimal('5.00'),
            unit_price=Decimal('50.00'),
            discount=Decimal('0.00'),
            state=SalesOrderLineStates.DRAFT
        )
        
        # Confirmar pedido
        self.order.confirm_order(self.user, 'Testing multiple lines')
        
        # Verificar reservas para ambos productos
        reservations = StockReservation.objects.filter(
            reserved_for=f"SO-{self.order.number}",
            status='active'
        )
        self.assertEqual(reservations.count(), 2)
        
        # Verificar cantidades reservadas
        reservation1 = reservations.filter(product=self.product).first()
        reservation2 = reservations.filter(product=product2).first()
        self.assertEqual(reservation1.quantity, Decimal('10.00'))
        self.assertEqual(reservation2.quantity, Decimal('5.00'))

    def test_stock_insufficient_error_handling(self):
        """Test manejo de errores cuando no hay stock suficiente"""
        # Modificar cantidad a más del stock disponible
        self.order_line.quantity = Decimal('60.00')
        self.order_line.save()
        # Intentar confirmar pedido con stock insuficiente
        with self.assertRaises(ValidationError):
            self.order.confirm_order(self.user, 'Testing insufficient stock')
        # Verificar que el pedido sigue en estado draft
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, SalesOrderStates.DRAFT)
        # Verificar que no se crearon reservas
        reservations = StockReservation.objects.filter(
            reserved_for=f"SO-{self.order.number}",
            status='active'
        )
        self.assertEqual(reservations.count(), 0)

    def test_stock_move_error_handling(self):
        """Test manejo de errores en movimientos de stock"""
        # Confirmar pedido
        self.order.confirm_order(self.user, 'Testing error handling')
        # Iniciar procesamiento
        self.order.start_processing(self.user, 'Start processing')
        # Marcar como listo para entregar
        self.order.mark_ready_to_deliver(self.user, 'Ready to deliver')
        # Eliminar stock para simular error
        self.stock_quant.delete()
        # Intentar entregar (debe fallar)
        with self.assertRaises(ValidationError):
            self.order.mark_delivered(self.user, 'Testing error handling')
        # Verificar que el pedido sigue en estado ready_to_deliver
        self.order.refresh_from_db()
        self.assertEqual(self.order.state, SalesOrderStates.READY_TO_DELIVER)

    def test_stock_summary_detailed_information(self):
        """Test información detallada del resumen de stock"""
        # Agregar más stock
        self.stock_quant.quantity = Decimal('100.00')
        self.stock_quant.save()
        
        # Obtener resumen
        summary = SalesInventoryValidator.get_stock_summary(self.order)
        
        # Verificar estructura del resumen
        self.assertIn('lines', summary)
        self.assertIn('total_available', summary)
        self.assertIn('total_reserved', summary)
        self.assertIn('can_confirm', summary)
        self.assertIn('can_deliver', summary)
        
        # Verificar información de línea
        line_summary = summary['lines'][0]
        self.assertEqual(line_summary['product_sku'], 'TP001')
        self.assertEqual(line_summary['requested_quantity'], Decimal('10.00'))
        self.assertEqual(line_summary['available_quantity'], Decimal('100.00'))
        self.assertEqual(line_summary['stock_status'], 'sufficient')
        
        # Verificar totales
        self.assertEqual(summary['total_available'], Decimal('100.00'))
        self.assertEqual(summary['total_reserved'], Decimal('0.00'))
        self.assertTrue(summary['can_confirm'])
        self.assertFalse(summary['can_deliver'])

    def test_stock_reservation_cleanup(self):
        """Test limpieza de reservas de stock"""
        # Confirmar pedido
        self.order.confirm_order(self.user, 'Testing cleanup')
        # Iniciar procesamiento
        self.order.start_processing(self.user, 'Start processing')
        # Marcar como listo para entregar
        self.order.mark_ready_to_deliver(self.user, 'Ready to deliver')
        # Entregar pedido
        self.order.mark_delivered(self.user, 'Delivered')
        # Marcar como facturado
        self.order.mark_invoiced(self.user, 'Invoiced')
        # Marcar como pagado
        self.order.mark_paid(self.user, 'Paid')
        # Completar pedido
        self.order.mark_completed(self.user, 'Testing cleanup')
        # Verificar que se liberaron las reservas
        self.assertEqual(
            StockReservation.objects.filter(
                reserved_for=f"SO-{self.order.number}",
                status='active'
            ).count(), 0
        )
        # Verificar que se actualizó StockQuant
        self.stock_quant.refresh_from_db()
        self.assertEqual(self.stock_quant.reserved_quantity, Decimal('0.00')) 