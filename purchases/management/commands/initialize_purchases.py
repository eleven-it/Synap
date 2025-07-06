from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from purchases.models import (
    Supplier, PurchaseRequest, PurchaseRequestLine, PurchaseQuotation,
    PurchaseQuotationLine, PurchaseOrder, PurchaseOrderLine, PurchaseReceipt,
    SupplierRating, ApprovalWorkflow, ApprovalLevel
)
from purchases.services import PurchaseService, SupplierService, ApprovalService, QuotationService

User = get_user_model()


class Command(BaseCommand):
    help = 'Inicializa datos de prueba para el módulo de compras'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=int,
            help='ID de la empresa para la cual crear los datos',
        )
        parser.add_argument(
            '--user',
            type=int,
            help='ID del usuario que ejecuta la inicialización',
        )

    def handle(self, *args, **options):
        empresa_id = options['empresa']
        user_id = options['user']

        if not empresa_id:
            self.stdout.write(
                self.style.ERROR('Debe especificar el ID de la empresa con --empresa')
            )
            return

        if not user_id:
            self.stdout.write(
                self.style.ERROR('Debe especificar el ID del usuario con --user')
            )
            return

        try:
            empresa = Empresa.objects.get(id=empresa_id)
            user = User.objects.get(id=user_id)
        except (Empresa.DoesNotExist, User.DoesNotExist) as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Inicializando datos de compras para empresa: {empresa.name}')
        )

        # Crear proveedores de prueba
        suppliers = self._create_suppliers(empresa, user)
        
        # Crear flujos de aprobación
        workflows = self._create_approval_workflows(empresa, user)
        
        # Crear solicitudes de compra
        requests = self._create_purchase_requests(empresa, user, suppliers)
        
        # Crear cotizaciones
        quotations = self._create_quotations(empresa, user, requests, suppliers)
        
        # Crear órdenes de compra
        orders = self._create_purchase_orders(empresa, user, requests, quotations)
        
        # Crear recepciones
        receipts = self._create_receipts(empresa, user, orders)
        
        # Crear evaluaciones de proveedores
        ratings = self._create_supplier_ratings(empresa, user, orders)

        self.stdout.write(
            self.style.SUCCESS(
                f'Inicialización completada:\n'
                f'- {len(suppliers)} proveedores\n'
                f'- {len(workflows)} flujos de aprobación\n'
                f'- {len(requests)} solicitudes de compra\n'
                f'- {len(quotations)} cotizaciones\n'
                f'- {len(orders)} órdenes de compra\n'
                f'- {len(receipts)} recepciones\n'
                f'- {len(ratings)} evaluaciones de proveedores'
            )
        )

    def _create_suppliers(self, empresa, user):
        """Crear proveedores de prueba"""
        suppliers_data = [
            {
                'name': 'Proveedor ABC S.A.',
                'code': 'ABC001',
                'contact_person': 'Juan Pérez',
                'email': 'juan.perez@abc.com',
                'phone': '+54 11 1234-5678',
                'address': 'Av. Corrientes 1234, CABA',
                'payment_terms': 'Net 30',
                'rating_class': 'good'
            },
            {
                'name': 'Distribuidora XYZ Ltda.',
                'code': 'XYZ002',
                'contact_person': 'María González',
                'email': 'maria.gonzalez@xyz.com',
                'phone': '+54 11 9876-5432',
                'address': 'Belgrano 567, CABA',
                'payment_terms': 'Net 60',
                'rating_class': 'excellent'
            },
            {
                'name': 'Comercial DEF S.R.L.',
                'code': 'DEF003',
                'contact_person': 'Carlos Rodríguez',
                'email': 'carlos.rodriguez@def.com',
                'phone': '+54 11 5555-1234',
                'address': 'San Martín 890, CABA',
                'payment_terms': 'Net 45',
                'rating_class': 'fair'
            }
        ]

        suppliers = []
        for data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                empresa=empresa,
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'contact_person': data['contact_person'],
                    'email': data['email'],
                    'phone': data['phone'],
                    'address': data['address'],
                    'payment_terms': data['payment_terms'],
                    'rating_class': data['rating_class'],
                    'created_by': user
                }
            )
            suppliers.append(supplier)
            if created:
                self.stdout.write(f'Creado proveedor: {supplier.name}')

        return suppliers

    def _create_approval_workflows(self, empresa, user):
        """Crear flujos de aprobación de prueba"""
        workflows_data = [
            {
                'name': 'Aprobación Estándar',
                'description': 'Flujo estándar para compras menores a $100,000',
                'min_amount': 0,
                'max_amount': 100000,
                'levels': [
                    {
                        'name': 'Supervisor',
                        'priority': 1,
                        'approval_type': 'role',
                        'roles': ['supervisor'],
                        'min_approvals': 1
                    }
                ]
            },
            {
                'name': 'Aprobación Alta',
                'description': 'Flujo para compras mayores a $100,000',
                'min_amount': 100000,
                'max_amount': None,
                'levels': [
                    {
                        'name': 'Supervisor',
                        'priority': 1,
                        'approval_type': 'role',
                        'roles': ['supervisor'],
                        'min_approvals': 1
                    },
                    {
                        'name': 'Gerente',
                        'priority': 2,
                        'approval_type': 'role',
                        'roles': ['manager'],
                        'min_approvals': 1
                    }
                ]
            }
        ]

        workflows = []
        for data in workflows_data:
            workflow, created = ApprovalWorkflow.objects.get_or_create(
                empresa=empresa,
                name=data['name'],
                defaults={
                    'description': data['description'],
                    'min_amount': data['min_amount'],
                    'max_amount': data['max_amount'],
                    'created_by': user
                }
            )
            
            if created:
                # Crear niveles
                for level_data in data['levels']:
                    ApprovalLevel.objects.create(
                        workflow=workflow,
                        name=level_data['name'],
                        priority=level_data['priority'],
                        approval_type=level_data['approval_type'],
                        roles=level_data['roles'],
                        min_approvals=level_data['min_approvals']
                    )
                
                self.stdout.write(f'Creado flujo de aprobación: {workflow.name}')
            
            workflows.append(workflow)

        return workflows

    def _create_purchase_requests(self, empresa, user, suppliers):
        """Crear solicitudes de compra de prueba"""
        from inventory.models import ProductVariant
        from core.models import Currency, UnitOfMeasure

        # Obtener productos, monedas y unidades de medida
        products = ProductVariant.objects.filter(empresa=empresa)[:5]
        currency = Currency.objects.filter(empresa=empresa).first()
        uom = UnitOfMeasure.objects.filter(empresa=empresa).first()

        if not products or not currency or not uom:
            self.stdout.write(
                self.style.WARNING('No hay productos, monedas o unidades de medida disponibles')
            )
            return []

        requests_data = [
            {
                'title': 'Compra de Materiales de Oficina',
                'description': 'Materiales básicos para el funcionamiento diario',
                'priority': 'medium',
                'required_date': timezone.now().date() + timedelta(days=30),
                'supplier': suppliers[0] if suppliers else None,
                'lines': [
                    {'product': products[0], 'quantity': 100, 'estimated_price': 15.50},
                    {'product': products[1], 'quantity': 50, 'estimated_price': 25.00},
                ]
            },
            {
                'title': 'Compra de Equipos Informáticos',
                'description': 'Equipos para renovación de hardware',
                'priority': 'high',
                'required_date': timezone.now().date() + timedelta(days=45),
                'supplier': suppliers[1] if len(suppliers) > 1 else None,
                'lines': [
                    {'product': products[2], 'quantity': 10, 'estimated_price': 1500.00},
                    {'product': products[3], 'quantity': 5, 'estimated_price': 800.00},
                ]
            }
        ]

        requests = []
        for data in requests_data:
            request = PurchaseRequest.objects.create(
                empresa=empresa,
                branch=user.branch,
                title=data['title'],
                description=data['description'],
                priority=data['priority'],
                required_date=data['required_date'],
                supplier=data['supplier'],
                currency=currency,
                requested_by=user
            )

            # Crear líneas
            for line_data in data['lines']:
                PurchaseRequestLine.objects.create(
                    purchase_request=request,
                    product_variant=line_data['product'],
                    quantity=line_data['quantity'],
                    unit_of_measure=uom,
                    estimated_unit_price=line_data['estimated_price'],
                    currency=currency
                )

            requests.append(request)
            self.stdout.write(f'Creada solicitud: {request.title}')

        return requests

    def _create_quotations(self, empresa, user, requests, suppliers):
        """Crear cotizaciones de prueba"""
        quotations = []
        
        for request in requests:
            if not request.supplier:
                continue
                
            # Crear cotización para cada solicitud
            quotation = PurchaseQuotation.objects.create(
                empresa=empresa,
                branch=user.branch,
                supplier=request.supplier,
                purchase_request=request,
                valid_until=timezone.now().date() + timedelta(days=15),
                currency=request.currency,
                payment_terms='Net 30',
                delivery_terms='FOB',
                delivery_time=10,
                created_by=user
            )

            # Crear líneas de cotización
            for line in request.lines.all():
                PurchaseQuotationLine.objects.create(
                    quotation=quotation,
                    request_line=line,
                    product_variant=line.product_variant,
                    quantity=line.quantity,
                    unit_of_measure=line.unit_of_measure,
                    unit_price=line.estimated_unit_price * 0.95,  # 5% descuento
                    discount_percentage=5,
                    tax_percentage=21,  # IVA
                    description=line.description
                )

            quotation.calculate_totals()
            quotations.append(quotation)
            self.stdout.write(f'Creada cotización: {quotation.quotation_number}')

        return quotations

    def _create_purchase_orders(self, empresa, user, requests, quotations):
        """Crear órdenes de compra de prueba"""
        orders = []
        
        for request in requests:
            if request.status != 'approved':
                # Aprobar solicitud automáticamente
                request.status = 'approved'
                request.approved_by = user
                request.approved_date = timezone.now().date()
                request.save()

            # Buscar cotización correspondiente
            quotation = next((q for q in quotations if q.purchase_request == request), None)
            
            # Crear orden
            order = PurchaseOrder.objects.create(
                empresa=empresa,
                branch=user.branch,
                supplier=request.supplier,
                purchase_request=request,
                quotation=quotation,
                expected_delivery_date=request.required_date,
                currency=request.currency,
                payment_terms=request.supplier.payment_terms if request.supplier else 'Net 30',
                created_by=user
            )

            # Crear líneas de orden
            for line in request.lines.all():
                PurchaseOrderLine.objects.create(
                    purchase_order=order,
                    request_line=line,
                    product_variant=line.product_variant,
                    quantity=line.quantity,
                    unit_of_measure=line.unit_of_measure,
                    unit_price=line.estimated_unit_price,
                    tax_percentage=21
                )

            order.calculate_totals()
            orders.append(order)
            self.stdout.write(f'Creada orden: {order.order_number}')

        return orders

    def _create_receipts(self, empresa, user, orders):
        """Crear recepciones de prueba"""
        receipts = []
        
        for order in orders:
            if order.status in ['confirmed', 'partially_received']:
                # Crear recepción parcial para algunas líneas
                for line in order.lines.all()[:2]:  # Solo las primeras 2 líneas
                    if line.remaining_quantity > 0:
                        receipt = PurchaseReceipt.objects.create(
                            empresa=empresa,
                            branch=user.branch,
                            purchase_order_line=line,
                            quantity=line.remaining_quantity * 0.7,  # 70% de lo pendiente
                            lot_number=f'LOT-{order.order_number}-{line.id}',
                            expiration_date=timezone.now().date() + timedelta(days=365),
                            status='approved',
                            quality_score=8,
                            received_by=user,
                            inspected_by=user
                        )
                        receipts.append(receipt)
                        self.stdout.write(f'Creada recepción: {receipt.receipt_number}')

        return receipts

    def _create_supplier_ratings(self, empresa, user, orders):
        """Crear evaluaciones de proveedores de prueba"""
        ratings = []
        
        for order in orders:
            if order.status in ['partially_received', 'received']:
                rating = SupplierRating.objects.create(
                    empresa=empresa,
                    supplier=order.supplier,
                    purchase_order=order,
                    period_start=order.order_date,
                    period_end=timezone.now().date(),
                    quality_score=8,
                    delivery_score=7,
                    communication_score=9,
                    price_score=8,
                    service_score=8,
                    quality_comments='Productos de buena calidad',
                    delivery_comments='Entrega a tiempo',
                    communication_comments='Excelente comunicación',
                    price_comments='Precios competitivos',
                    service_comments='Buen servicio al cliente',
                    general_comments='Proveedor recomendado',
                    recommendations='Mantener relación comercial',
                    would_recommend=True,
                    status='approved',
                    evaluated_by=user
                )
                ratings.append(rating)
                self.stdout.write(f'Creada evaluación: {rating.supplier.name}')

        return ratings 