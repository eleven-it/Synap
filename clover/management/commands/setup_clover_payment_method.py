"""
Comando para configurar Clover como método de pago
"""
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from sales.models import PaymentMethod, PaymentProcessor
from core.models import Empresa, Branch


class Command(BaseCommand):
    help = 'Configurar Clover como método de pago en el sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de la empresa para configurar Clover',
        )
        parser.add_argument(
            '--branch-id',
            type=int,
            help='ID de la sucursal para configurar Clover',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin ejecutar cambios',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔧 Configurando Clover como método de pago...')
        
        # Obtener empresa y sucursal
        empresa = None
        branch = None
        
        if options['empresa_id']:
            try:
                empresa = Empresa.objects.get(id=options['empresa_id'])
            except Empresa.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Empresa con ID {options["empresa_id"]} no encontrada'))
                return
        else:
            # Usar la primera empresa activa
            empresa = Empresa.objects.filter(activa=True).first()
            if not empresa:
                self.stdout.write(self.style.ERROR('❌ No se encontró ninguna empresa activa'))
                return
        
        if options['branch_id']:
            try:
                branch = Branch.objects.get(id=options['branch_id'], empresa=empresa)
            except Branch.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Sucursal con ID {options["branch_id"]} no encontrada'))
                return
        else:
            # Usar la primera sucursal activa de la empresa
            branch = Branch.objects.filter(empresa=empresa, active=True).first()
            if not branch:
                self.stdout.write(self.style.ERROR('❌ No se encontró ninguna sucursal activa'))
                return
        
        self.stdout.write(f'🏢 Empresa: {empresa.name}')
        self.stdout.write(f'🏪 Sucursal: {branch.name}')
        
        if options['dry_run']:
            self.stdout.write('🔍 Modo dry-run - no se realizarán cambios')
        
        # 1. Crear procesador de pago Clover
        self.setup_clover_processor(empresa, options['dry_run'])
        
        # 2. Crear métodos de pago Clover
        self.setup_clover_payment_methods(empresa, branch, options['dry_run'])
        
        self.stdout.write(self.style.SUCCESS('✅ Configuración de Clover completada'))

    def setup_clover_processor(self, empresa, dry_run=False):
        """Configurar procesador de pago Clover"""
        self.stdout.write('  🔧 Configurando procesador de pago Clover...')
        
        processor_data = {
            'name': 'Clover Payment Processor',
            'processor_type': 'clover',
            'is_active': True,
            'api_key': '',  # Se configurará manualmente
            'api_secret': '',  # Se configurará manualmente
            'webhook_url': '',  # Se configurará manualmente
            'webhook_secret': '',  # Se configurará manualmente
            'config': {
                'environment': 'sandbox',
                'merchant_id': '',
                'device_id': '',
                'supports_refunds': True,
                'supports_partial_refunds': True,
                'supports_installments': True,
                'max_installments': 12,
                'processing_time_hours': 0,
                'supported_currencies': ['USD', 'ARS'],
                'supported_countries': ['AR', 'US'],
            }
        }
        
        if not dry_run:
            processor, created = PaymentProcessor.objects.get_or_create(
                empresa=empresa,
                processor_type='clover',
                defaults=processor_data
            )
            
            if created:
                self.stdout.write(f'    ✅ Procesador Clover creado: {processor.name}')
            else:
                self.stdout.write(f'    ⚠️ Procesador Clover existente: {processor.name}')
        else:
            self.stdout.write(f'    🔍 Se crearía procesador: {processor_data["name"]}')

    def setup_clover_payment_methods(self, empresa, branch, dry_run=False):
        """Configurar métodos de pago Clover"""
        self.stdout.write('  💳 Configurando métodos de pago Clover...')
        
        payment_methods_data = [
            {
                'name': 'Clover Card',
                'code': 'CLOVER_CARD',
                'description': 'Pago con tarjeta a través de dispositivos Clover',
                'payment_type': 'card',
                'card_type': 'visa',
                'icon': 'credit_card',
                'color': '#10B981',
                'is_active': True,
                'is_default': False,
                'order': 10,
                'commission_percentage': 2.9,
                'fixed_commission': 0.30,
                'minimum_amount': 0.01,
                'maximum_amount': 0,
                'requires_card_number': True,
                'requires_expiry': True,
                'requires_cvv': True,
                'requires_installments': True,
                'max_installments': 12,
                'processing_time_hours': 0,
                'supports_refunds': True,
                'supports_partial_refunds': True,
                'processor_name': 'clover',
                'processor_config': {
                    'device_type': 'card_reader',
                    'supports_contactless': True,
                    'supports_chip': True,
                    'supports_magnetic_stripe': True,
                },
                'requires_3d_secure': False,
                'supports_tokenization': True,
                'supported_currencies': ['USD', 'ARS'],
                'supported_countries': ['AR', 'US'],
            },
            {
                'name': 'Clover Cash',
                'code': 'CLOVER_CASH',
                'description': 'Pago en efectivo registrado en Clover',
                'payment_type': 'cash',
                'icon': 'payments',
                'color': '#059669',
                'is_active': True,
                'is_default': False,
                'order': 11,
                'commission_percentage': 0,
                'fixed_commission': 0,
                'minimum_amount': 0.01,
                'maximum_amount': 0,
                'requires_reference': True,
                'processing_time_hours': 0,
                'supports_refunds': True,
                'supports_partial_refunds': True,
                'processor_name': 'clover',
                'processor_config': {
                    'device_type': 'cash_register',
                    'requires_cash_drawer': True,
                },
                'supported_currencies': ['USD', 'ARS'],
                'supported_countries': ['AR', 'US'],
            },
            {
                'name': 'Clover Check',
                'code': 'CLOVER_CHECK',
                'description': 'Pago con cheque a través de Clover',
                'payment_type': 'check',
                'icon': 'receipt',
                'color': '#DC2626',
                'is_active': True,
                'is_default': False,
                'order': 12,
                'commission_percentage': 0,
                'fixed_commission': 0,
                'minimum_amount': 0.01,
                'maximum_amount': 0,
                'requires_reference': True,
                'processing_time_hours': 72,
                'supports_refunds': True,
                'supports_partial_refunds': True,
                'processor_name': 'clover',
                'processor_config': {
                    'device_type': 'check_reader',
                    'requires_check_number': True,
                },
                'supported_currencies': ['USD', 'ARS'],
                'supported_countries': ['AR', 'US'],
            },
        ]
        
        for data in payment_methods_data:
            if not dry_run:
                payment_method, created = PaymentMethod.objects.get_or_create(
                    empresa=empresa,
                    code=data['code'],
                    defaults=data
                )
                
                if created:
                    payment_method.branches.add(branch)
                    self.stdout.write(f'    ✅ Método de pago creado: {payment_method.name}')
                else:
                    # Actualizar sucursales si no está asignada
                    if branch not in payment_method.branches.all():
                        payment_method.branches.add(branch)
                        self.stdout.write(f'    🔄 Sucursal agregada a: {payment_method.name}')
                    else:
                        self.stdout.write(f'    ⚠️ Método de pago existente: {payment_method.name}')
            else:
                self.stdout.write(f'    🔍 Se crearía método: {data["name"]} ({data["code"]})') 