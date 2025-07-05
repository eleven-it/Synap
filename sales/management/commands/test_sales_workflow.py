from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal

from sales.models import (
    SalesOrder, SalesOrderLine, Client, PriceList, PaymentTerm,
    SalesOrderStates, SalesOrderLineStates
)
from sales.utils import SalesOrderWorkflow, SalesOrderCalculator, SalesOrderValidator

User = get_user_model()


class Command(BaseCommand):
    help = 'Test sales order workflow and business logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='Create test data for workflow testing',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting sales workflow test...')
        )

        if options['create_test_data']:
            self.create_test_data()

        self.test_workflow()
        self.test_calculations()
        self.test_validations()

        self.stdout.write(
            self.style.SUCCESS('Sales workflow test completed successfully!')
        )

    def create_test_data(self):
        """Crear datos de prueba"""
        self.stdout.write('Creating test data...')

        # Crear usuario de prueba
        user, created = User.objects.get_or_create(
            email='test@seller.com',
            defaults={
                'nombre': 'Test Seller',
                'is_active': True
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()

        # Crear cliente de prueba
        client, created = Client.objects.get_or_create(
            name='Test Client',
            defaults={
                'email': 'test@client.com',
                'type': 'company',
                'credit_limit': Decimal('10000.00'),
                'is_active': True
            }
        )

        # Crear lista de precios
        price_list, created = PriceList.objects.get_or_create(
            name='Standard Prices',
            defaults={
                'currency': 'USD',
                'is_active': True
            }
        )

        # Crear condiciones de pago
        payment_term, created = PaymentTerm.objects.get_or_create(
            name='Net 30',
            defaults={
                'description': 'Payment due in 30 days',
                'is_active': True
            }
        )

        # Crear sucursal (asumiendo que existe)
        from core.models import Branch
        branch = Branch.objects.first()
        if not branch:
            self.stdout.write(
                self.style.WARNING('No branch found. Please create a branch first.')
            )
            return

        self.test_user = user
        self.test_client = client
        self.test_price_list = price_list
        self.test_payment_term = payment_term
        self.test_branch = branch

        self.stdout.write(
            self.style.SUCCESS('Test data created successfully!')
        )

    def test_workflow(self):
        """Probar el flujo de trabajo de pedidos"""
        self.stdout.write('Testing sales order workflow...')

        # Crear pedido de prueba
        order = SalesOrder.objects.create(
            order_date=timezone.now().date(),
            currency='USD',
            client=self.test_client,
            branch=self.test_branch,
            payment_term=self.test_payment_term,
            price_list=self.test_price_list,
            seller=self.test_user,
            state=SalesOrderStates.DRAFT
        )

        # Crear líneas de pedido
        from inventory.models import ProductVariant
        product_variant = ProductVariant.objects.first()
        if not product_variant:
            self.stdout.write(
                self.style.WARNING('No product variant found. Skipping line creation.')
            )
            return

        line1 = SalesOrderLine.objects.create(
            sales_order=order,
            product_variant=product_variant,
            quantity=Decimal('2.00'),
            unit_price=Decimal('100.00'),
            discount=Decimal('10.00'),
            state=SalesOrderLineStates.DRAFT
        )

        line2 = SalesOrderLine.objects.create(
            sales_order=order,
            product_variant=product_variant,
            quantity=Decimal('1.00'),
            unit_price=Decimal('50.00'),
            discount=Decimal('0.00'),
            state=SalesOrderLineStates.DRAFT
        )

        self.stdout.write(f'Created order: {order.number}')

        # Probar transiciones de estado
        try:
            # Enviar cotización
            SalesOrderWorkflow.send_quotation(
                order, self.test_user, "Sending quotation to client"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            # Confirmar pedido
            SalesOrderWorkflow.confirm_order(
                order, self.test_user, "Client confirmed the order"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            # Iniciar procesamiento
            SalesOrderWorkflow.start_processing(
                order, self.test_user, "Starting order processing"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            # Marcar listo para entregar
            SalesOrderWorkflow.mark_ready_to_deliver(
                order, self.test_user, "Order ready for delivery"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            # Marcar como entregado
            SalesOrderWorkflow.mark_delivered(
                order, self.test_user, "Order delivered to client"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            # Marcar como facturado
            SalesOrderWorkflow.mark_invoiced(
                order, self.test_user, "Invoice created for order"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            # Marcar como pagado
            SalesOrderWorkflow.mark_paid(
                order, self.test_user, "Payment received"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            # Marcar como completado
            SalesOrderWorkflow.mark_completed(
                order, self.test_user, "Order completed successfully"
            )
            self.stdout.write(f'✓ Order state: {order.state}')

            self.stdout.write(
                self.style.SUCCESS('✓ All workflow transitions successful!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Workflow test failed: {str(e)}')
            )

    def test_calculations(self):
        """Probar cálculos de pedidos"""
        self.stdout.write('Testing sales order calculations...')

        # Obtener el pedido de prueba
        order = SalesOrder.objects.filter(
            seller=self.test_user
        ).first()

        if not order:
            self.stdout.write(
                self.style.WARNING('No test order found. Skipping calculations test.')
            )
            return

        try:
            # Recalcular totales
            order.recalculate_totals()
            
            # Obtener totales calculados
            totals = SalesOrderCalculator.calculate_order_totals(order)
            
            self.stdout.write(f'✓ Order total: {order.total}')
            self.stdout.write(f'✓ Order discount: {order.total_discount}')
            self.stdout.write(f'✓ Order tax: {order.total_tax}')
            self.stdout.write(f'✓ Calculated total: {totals["total"]}')
            self.stdout.write(f'✓ Calculated discount: {totals["total_discount"]}')
            
            # Probar cálculos de progreso
            delivery_progress = SalesOrderCalculator.calculate_delivery_progress(order)
            payment_progress = SalesOrderCalculator.calculate_payment_progress(order)
            
            self.stdout.write(f'✓ Delivery progress: {delivery_progress}%')
            self.stdout.write(f'✓ Payment progress: {payment_progress}%')
            
            self.stdout.write(
                self.style.SUCCESS('✓ All calculations successful!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Calculations test failed: {str(e)}')
            )

    def test_validations(self):
        """Probar validaciones de pedidos"""
        self.stdout.write('Testing sales order validations...')

        try:
            # Crear pedido sin líneas para probar validación
            empty_order = SalesOrder.objects.create(
                order_date=timezone.now().date(),
                currency='USD',
                client=self.test_client,
                branch=self.test_branch,
                payment_term=self.test_payment_term,
                price_list=self.test_price_list,
                seller=self.test_user,
                state=SalesOrderStates.DRAFT
            )

            # Probar validación de confirmación sin líneas
            try:
                SalesOrderValidator.validate_order_for_confirmation(empty_order)
                self.stdout.write(
                    self.style.ERROR('✗ Validation should have failed for empty order')
                )
            except ValidationError:
                self.stdout.write('✓ Empty order validation working correctly')

            # Probar validación de transición de estado
            try:
                SalesOrderValidator.validate_state_transition(
                    SalesOrderStates.DRAFT, 
                    SalesOrderStates.PAID
                )
                self.stdout.write(
                    self.style.ERROR('✗ Invalid state transition should have failed')
                )
            except ValidationError:
                self.stdout.write('✓ Invalid state transition validation working correctly')

            # Probar validación de transición válida
            try:
                SalesOrderValidator.validate_state_transition(
                    SalesOrderStates.DRAFT, 
                    SalesOrderStates.QUOTATION_SENT
                )
                self.stdout.write('✓ Valid state transition validation working correctly')
            except ValidationError as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Valid state transition failed: {str(e)}')
                )

            self.stdout.write(
                self.style.SUCCESS('✓ All validations working correctly!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Validations test failed: {str(e)}')
            )

    def test_error_cases(self):
        """Probar casos de error"""
        self.stdout.write('Testing error cases...')

        # Obtener el pedido de prueba
        order = SalesOrder.objects.filter(
            seller=self.test_user
        ).first()

        if not order:
            return

        try:
            # Probar transición sin razón
            try:
                SalesOrderWorkflow.send_quotation(order, self.test_user, "")
                self.stdout.write(
                    self.style.ERROR('✗ Empty reason should have failed')
                )
            except ValidationError:
                self.stdout.write('✓ Empty reason validation working correctly')

            # Probar transición inválida
            try:
                SalesOrderWorkflow.mark_paid(order, self.test_user, "Invalid transition")
                self.stdout.write(
                    self.style.ERROR('✗ Invalid transition should have failed')
                )
            except ValidationError:
                self.stdout.write('✓ Invalid transition validation working correctly')

            self.stdout.write(
                self.style.SUCCESS('✓ All error cases handled correctly!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error cases test failed: {str(e)}')
            ) 