from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from core.models import Branch
from core.models.models import Empresa
from sales.models import (
    POSTerminal, POSPromotion, PriceList, PriceListItem,
    Client, POSSession, POSSale, POSSaleLine, POSPayment
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Configurar datos de prueba para el TPV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='ID de la empresa para configurar el TPV'
        )
        parser.add_argument(
            '--branch-id',
            type=int,
            help='ID de la sucursal para configurar el TPV'
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        branch_id = options.get('branch_id')

        if not company_id:
            # Buscar la primera empresa disponible
            company = Empresa.objects.first()
            if not company:
                self.stdout.write(
                    self.style.ERROR('No hay empresas configuradas. Configure una empresa primero.')
                )
                return
            company_id = company.id

        if not branch_id:
            # Buscar la primera sucursal de la empresa
            branch = Branch.objects.filter(empresa_id=company_id).first()
            if not branch:
                self.stdout.write(
                    self.style.ERROR('No hay sucursales configuradas para esta empresa.')
                )
                return
            branch_id = branch.id

        with transaction.atomic():
            self.setup_pos_data(company_id, branch_id)

    def setup_pos_data(self, company_id, branch_id):
        """Configurar datos de prueba del TPV"""
        company = Empresa.objects.get(id=company_id)
        branch = Branch.objects.get(id=branch_id)

        self.stdout.write(f'Configurando TPV para empresa: {company.nombre}')
        self.stdout.write(f'Sucursal: {branch.name}')

        # 1. Crear terminales de punto de venta
        self.create_pos_terminals(branch)

        # 2. Crear lista de precios si no existe
        self.create_price_list(branch)

        # 3. Crear promociones
        self.create_promotions()

        # 4. Crear clientes de prueba
        self.create_test_clients(company)

        # 5. Crear sesión de prueba
        self.create_test_session(branch)

        self.stdout.write(
            self.style.SUCCESS('✅ Datos de TPV configurados correctamente')
        )

    def create_pos_terminals(self, branch):
        """Crear terminales de punto de venta"""
        terminals_data = [
            {
                'name': 'Terminal Principal',
                'code': 'TPV001',
                'electronic_invoice': True,
                'fiscal_printer': True,
                'scale_integration': True,
            },
            {
                'name': 'Terminal Secundario',
                'code': 'TPV002',
                'electronic_invoice': False,
                'fiscal_printer': False,
                'scale_integration': False,
            },
            {
                'name': 'Terminal Móvil',
                'code': 'TPV003',
                'electronic_invoice': False,
                'fiscal_printer': False,
                'scale_integration': False,
            }
        ]

        for terminal_data in terminals_data:
            terminal, created = POSTerminal.objects.get_or_create(
                code=terminal_data['code'],
                defaults={
                    'name': terminal_data['name'],
                    'branch': branch,
                    'is_active': True,
                    'electronic_invoice': terminal_data['electronic_invoice'],
                    'fiscal_printer': terminal_data['fiscal_printer'],
                    'scale_integration': terminal_data['scale_integration'],
                }
            )
            
            if created:
                self.stdout.write(f'  ✅ Terminal creado: {terminal.name}')
            else:
                self.stdout.write(f'  ℹ️  Terminal existente: {terminal.name}')

    def create_price_list(self, branch):
        """Crear lista de precios para la sucursal"""
        price_list, created = PriceList.objects.get_or_create(
            name='Lista de Precios Principal',
            defaults={
                'currency': 'ARS',
                'is_active': True,
                'valid_from': timezone.now().date(),
                'valid_to': (timezone.now() + timedelta(days=365)).date(),
            }
        )

        if created:
            self.stdout.write(f'  ✅ Lista de precios creada: {price_list.name}')
        else:
            self.stdout.write(f'  ℹ️  Lista de precios existente: {price_list.name}')

        # Asignar lista de precios a la sucursal si no tiene una
        if not hasattr(branch, 'default_price_list') or not branch.default_price_list:
            branch.default_price_list = price_list
            branch.save()
            self.stdout.write(f'  ✅ Lista de precios asignada a sucursal')

    def create_promotions(self):
        """Crear promociones de prueba"""
        promotions_data = [
            {
                'code': 'DESCUENTO10',
                'name': 'Descuento 10%',
                'promotion_type': 'discount_percentage',
                'is_active': True,
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=30),
                'minimum_amount': 1000.0,
                'configuration': {'percentage': 10.0},
            },
            {
                'code': 'DESCUENTO20',
                'name': 'Descuento 20%',
                'promotion_type': 'discount_percentage',
                'is_active': True,
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=30),
                'minimum_amount': 2000.0,
                'configuration': {'percentage': 20.0},
            },
            {
                'code': 'DESCUENTO50',
                'name': 'Descuento $50',
                'promotion_type': 'discount_amount',
                'is_active': True,
                'valid_from': timezone.now(),
                'valid_to': timezone.now() + timedelta(days=30),
                'minimum_amount': 500.0,
                'configuration': {'amount': 50.0},
            }
        ]

        for promo_data in promotions_data:
            promotion, created = POSPromotion.objects.get_or_create(
                code=promo_data['code'],
                defaults=promo_data
            )
            
            if created:
                self.stdout.write(f'  ✅ Promoción creada: {promotion.name}')
            else:
                self.stdout.write(f'  ℹ️  Promoción existente: {promotion.name}')

    def create_test_clients(self, company):
        """Crear clientes de prueba"""
        clients_data = [
            {
                'name': 'Cliente Consumidor Final',
                'tax_id': '99999999',
                'fiscal_conditions': 'Consumidor Final',
                'is_customer': True,
            },
            {
                'name': 'Empresa ABC S.A.',
                'tax_id': '30-12345678-9',
                'fiscal_conditions': 'Responsable Inscripto',
                'is_customer': True,
            },
            {
                'name': 'Comercio XYZ',
                'tax_id': '20-87654321-0',
                'fiscal_conditions': 'Responsable Inscripto',
                'is_customer': True,
            }
        ]

        for client_data in clients_data:
            client, created = Client.objects.get_or_create(
                tax_id=client_data['tax_id'],
                defaults={
                    'name': client_data['name'],
                    'fiscal_conditions': client_data['fiscal_conditions'],
                    'is_customer': client_data['is_customer'],
                    'empresa': company,
                }
            )
            
            if created:
                self.stdout.write(f'  ✅ Cliente creado: {client.name}')
            else:
                self.stdout.write(f'  ℹ️  Cliente existente: {client.name}')

    def create_test_session(self, branch):
        """Crear sesión de prueba"""
        # Buscar un usuario administrador
        user = User.objects.filter(is_staff=True).first()
        if not user:
            self.stdout.write(
                self.style.WARNING('No hay usuarios administradores para crear sesión de prueba')
            )
            return

        # Buscar un terminal
        terminal = POSTerminal.objects.filter(branch=branch, is_active=True).first()
        if not terminal:
            self.stdout.write(
                self.style.WARNING('No hay terminales activos para crear sesión de prueba')
            )
            return

        # Crear sesión de prueba
        session, created = POSSession.objects.get_or_create(
            number=f'SES{branch.code}{terminal.code}000001',
            defaults={
                'operator': user,
                'branch': branch,
                'pos_terminal': terminal,
                'state': 'open',
                'opening_amount': 1000.0,
                'opened_at': timezone.now(),
            }
        )

        if created:
            self.stdout.write(f'  ✅ Sesión de prueba creada: {session.number}')
        else:
            self.stdout.write(f'  ℹ️  Sesión de prueba existente: {session.number}')

        # Crear venta de prueba si no existe
        if not session.sales.exists():
            self.create_test_sale(session)

    def create_test_sale(self, session):
        """Crear venta de prueba"""
        # Buscar un cliente
        client = Client.objects.filter(is_customer=True).first()
        
        sale = POSSale.objects.create(
            session=session,
            operator=session.operator,
            client=client,
            is_occasional_client=False,
            state='draft',
            subtotal=0.0,
            total_discount=0.0,
            total_tax=0.0,
            total=0.0,
            total_paid=0.0,
            price_list=session.branch.default_price_list,
            currency='ARS',
            sale_date=timezone.now(),
        )

        self.stdout.write(f'  ✅ Venta de prueba creada: {sale.number}')

        # Crear líneas de venta de prueba (solo si hay productos disponibles)
        try:
            from inventory.models import ProductVariant
            
            products = ProductVariant.objects.filter(is_active=True)[:3]
            if products:
                for i, product in enumerate(products):
                    quantity = i + 1
                    unit_price = 100.0 + (i * 50)
                    subtotal = quantity * unit_price
                    
                    line = POSSaleLine.objects.create(
                        sale=sale,
                        product_variant=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        discount_percentage=0.0,
                        tax_percentage=21.0,
                        subtotal=subtotal,
                        discount_amount=0.0,
                        tax_amount=subtotal * 0.21,
                        barcode=product.barcode or '',
                        description=product.product.name,
                    )
                
                # Recalcular totales
                sale.recalculate_totals()
                sale.save()
                
                self.stdout.write(f'  ✅ Líneas de venta agregadas')
            else:
                self.stdout.write(f'  ℹ️  No hay productos disponibles para líneas de venta')
                
        except ImportError:
            self.stdout.write(f'  ℹ️  Módulo inventory no disponible, saltando líneas de venta') 