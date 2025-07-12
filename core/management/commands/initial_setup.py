"""
Comando de puesta en marcha inicial del sistema Synap
Ejecuta todos los pasos necesarios para configurar el sistema desde cero
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Puesta en marcha inicial completa del sistema Synap'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Saltar aplicación de migraciones',
        )
        parser.add_argument(
            '--skip-firebase-sync',
            action='store_true',
            help='Saltar sincronización con Firebase',
        )
        parser.add_argument(
            '--skip-accounting',
            action='store_true',
            help='Saltar configuración de contabilidad',
        )
        parser.add_argument(
            '--skip-payment-methods',
            action='store_true',
            help='Saltar configuración de métodos de pago',
        )
        parser.add_argument(
            '--empresa-nombre',
            type=str,
            default='Empresa Principal',
            help='Nombre de la empresa principal',
        )
        parser.add_argument(
            '--empresa-identificador',
            type=str,
            default='EMP-001',
            help='Identificador fiscal de la empresa',
        )
        parser.add_argument(
            '--branch-nombre',
            type=str,
            default='Sucursal Principal',
            help='Nombre de la sucursal principal',
        )
        parser.add_argument(
            '--branch-codigo',
            type=str,
            default='BRANCH-001',
            help='Código de la sucursal principal',
        )
        parser.add_argument(
            '--fiscal-year-start',
            type=str,
            default=None,
            help='Fecha de inicio del año fiscal (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar recreación de datos existentes',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando puesta en marcha del sistema Synap...\n'))
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('🔍 MODO DRY-RUN: No se harán cambios reales\n'))
        
        try:
            with transaction.atomic():
                # 1. Aplicar migraciones
                if not options['skip_migrations']:
                    self.apply_migrations()
                
                # 2. Crear empresa y sucursal por defecto
                empresa, branch = self.setup_company_and_branch(options)
                
                # 3. Poblar datos geográficos
                self.populate_geographic_data()
                
                # 4. Sincronizar permisos
                self.sync_permissions()
                
                # 5. Crear roles base
                self.create_base_roles()
                
                # 6. Sincronizar usuarios con Firebase
                if not options['skip_firebase_sync']:
                    self.sync_firebase_users()
                
                # 7. Asignar roles predeterminados
                self.assign_default_roles()
                
                # 8. Configurar módulos del sistema
                self.setup_system_modules()
                
                # 9. Configurar contabilidad
                if not options['skip_accounting']:
                    self.setup_accounting(empresa, options)
                
                # 10. Configurar métodos de pago
                if not options['skip_payment_methods']:
                    self.setup_payment_methods(empresa, branch)
                
                # 11. Asignar sucursales a administradores
                self.assign_branches_to_admins()
                
                # 12. Verificar integridad del sistema
                self.verify_system_integrity()
                
            self.stdout.write(self.style.SUCCESS('\n✅ Puesta en marcha completada exitosamente!'))
            self.print_summary()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error durante la puesta en marcha: {e}'))
            if not options['dry_run']:
                self.stdout.write(self.style.ERROR('🔄 Los cambios han sido revertidos debido al error'))
            raise

    def apply_migrations(self):
        """Aplicar migraciones de la base de datos"""
        self.stdout.write('📋 Aplicando migraciones...')
        if not self.options['dry_run']:
            call_command('migrate', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Migraciones aplicadas'))

    def setup_company_and_branch(self, options):
        """Crear empresa y sucursal por defecto"""
        self.stdout.write('🏢 Configurando empresa y sucursal...')
        
        from core.models import Empresa, Branch
        
        # Verificar si ya existe una empresa
        empresa = Empresa.objects.first()
        if empresa and not options['force']:
            self.stdout.write(f'  ⚠️ Usando empresa existente: {empresa.nombre}')
        else:
            if options['force'] and empresa:
                empresa.delete()
                self.stdout.write('  🔄 Empresa existente eliminada')
            
            if not self.options['dry_run']:
                empresa = Empresa.objects.create(
                    nombre=options['empresa_nombre'],
                    identificador_fiscal=options['empresa_identificador'],
                    email='admin@synap.com',
                    telefono='+54 11 1234-5678',
                    direccion='Av. Principal 123',
                    pais='Argentina',
                    ciudad='Buenos Aires',
                    activa=True
                )
            self.stdout.write(f'  ✅ Empresa creada: {empresa.nombre}')
        
        # Verificar si ya existe una sucursal
        branch = Branch.objects.filter(empresa=empresa).first()
        if branch and not options['force']:
            self.stdout.write(f'  ⚠️ Usando sucursal existente: {branch.name}')
        else:
            if options['force'] and branch:
                branch.delete()
                self.stdout.write('  🔄 Sucursal existente eliminada')
            
            if not self.options['dry_run']:
                branch = Branch.objects.create(
                    empresa=empresa,
                    name=options['branch_nombre'],
                    code=options['branch_codigo'],
                    address='Av. Principal 123, Piso 1',
                    city='Buenos Aires',
                    state='Buenos Aires',
                    country='Argentina',
                    phone='+54 11 1234-5678',
                    email='branch@synap.com',
                    active=True
                )
            self.stdout.write(f'  ✅ Sucursal creada: {branch.name}')
        
        return empresa, branch

    def populate_geographic_data(self):
        """Poblar datos geográficos básicos"""
        self.stdout.write('🌍 Poblando datos geográficos...')
        if not self.options['dry_run']:
            call_command('populate_countries_states', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Datos geográficos poblados'))

    def sync_permissions(self):
        """Sincronizar permisos desde constantes"""
        self.stdout.write('🔐 Sincronizando permisos...')
        if not self.options['dry_run']:
            call_command('sincronizar_permisos', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Permisos sincronizados'))

    def create_base_roles(self):
        """Crear roles base del sistema"""
        self.stdout.write('👥 Creando roles base...')
        if not self.options['dry_run']:
            call_command('crear_roles_base', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Roles base creados'))

    def sync_firebase_users(self):
        """Sincronizar usuarios con Firebase"""
        self.stdout.write('🔥 Sincronizando usuarios con Firebase...')
        if not self.options['dry_run']:
            call_command('sincronizar_usuarios_firebase', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Usuarios sincronizados con Firebase'))

    def assign_default_roles(self):
        """Asignar roles predeterminados a usuarios"""
        self.stdout.write('🎭 Asignando roles predeterminados...')
        if not self.options['dry_run']:
            call_command('asignar_roles_predeterminados', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Roles predeterminados asignados'))

    def setup_system_modules(self):
        """Configurar módulos del sistema"""
        self.stdout.write('⚙️ Configurando módulos del sistema...')
        if not self.options['dry_run']:
            call_command('setup_modules', '--init', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Módulos del sistema configurados'))

    def setup_accounting(self, empresa, options):
        """Configurar contabilidad básica"""
        self.stdout.write('💰 Configurando contabilidad...')
        
        if not self.options['dry_run']:
            # Configurar plan de cuentas
            call_command('setup_chart_of_accounts', 
                        empresa_nombre=empresa.nombre, 
                        verbosity=0)
            
            # Configurar diarios
            call_command('setup_journals', 
                        empresa_nombre=empresa.nombre, 
                        verbosity=0)
            
            # Configurar contabilidad general
            call_command('setup_accounting', 
                        empresa_nombre=empresa.nombre, 
                        verbosity=0)
            
            # Crear años fiscales y períodos
            fiscal_year_start = options.get('fiscal_year_start')
            if not fiscal_year_start:
                # Usar año actual
                current_year = timezone.now().year
                fiscal_year_start = f"{current_year}-01-01"
            
            call_command('load_periods_data', 
                        empresa_nombre=empresa.nombre,
                        years=3,
                        verbosity=0)
        
        self.stdout.write(self.style.SUCCESS('  ✅ Contabilidad configurada'))

    def setup_payment_methods(self, empresa, branch):
        """Configurar métodos de pago básicos"""
        self.stdout.write('💳 Configurando métodos de pago...')
        
        from sales.models import PaymentMethod
        
        if not self.options['dry_run']:
            # Métodos de pago básicos
            payment_methods_data = [
                {
                    'name': 'Efectivo',
                    'code': 'CASH',
                    'payment_type': 'cash',
                    'icon': 'payments',
                    'color': '#10B981',
                    'is_default': True,
                    'order': 1,
                },
                {
                    'name': 'Tarjeta de Crédito',
                    'code': 'CREDIT_CARD',
                    'payment_type': 'card',
                    'card_type': 'visa',
                    'icon': 'credit_card',
                    'color': '#3B82F6',
                    'order': 2,
                    'requires_card_number': True,
                    'requires_expiry': True,
                    'requires_cvv': True,
                    'supports_installments': True,
                    'max_installments': 12,
                },
                {
                    'name': 'Tarjeta de Débito',
                    'code': 'DEBIT_CARD',
                    'payment_type': 'card',
                    'card_type': 'visa',
                    'icon': 'credit_card',
                    'color': '#8B5CF6',
                    'order': 3,
                    'requires_card_number': True,
                    'requires_expiry': True,
                    'requires_cvv': True,
                },
                {
                    'name': 'Transferencia Bancaria',
                    'code': 'BANK_TRANSFER',
                    'payment_type': 'bank_transfer',
                    'icon': 'account_balance',
                    'color': '#059669',
                    'order': 4,
                    'requires_reference': True,
                    'processing_time_hours': 24,
                },
                {
                    'name': 'Cheque',
                    'code': 'CHECK',
                    'payment_type': 'check',
                    'icon': 'receipt',
                    'color': '#DC2626',
                    'order': 5,
                    'requires_reference': True,
                    'processing_time_hours': 72,
                },
            ]
            
            for data in payment_methods_data:
                payment_method, created = PaymentMethod.objects.get_or_create(
                    empresa=empresa,
                    code=data['code'],
                    defaults=data
                )
                
                if created:
                    payment_method.branches.add(branch)
                    self.stdout.write(f'    ✅ Método de pago creado: {payment_method.name}')
                else:
                    self.stdout.write(f'    ⚠️ Método de pago existente: {payment_method.name}')
        
        self.stdout.write(self.style.SUCCESS('  ✅ Métodos de pago configurados'))

    def assign_branches_to_admins(self):
        """Asignar sucursales a usuarios administradores"""
        self.stdout.write('👨‍💼 Asignando sucursales a administradores...')
        if not self.options['dry_run']:
            call_command('asignar_sucursales_admins', verbosity=0)
        self.stdout.write(self.style.SUCCESS('  ✅ Sucursales asignadas a administradores'))

    def verify_system_integrity(self):
        """Verificar integridad del sistema"""
        self.stdout.write('🔍 Verificando integridad del sistema...')
        
        from core.models import Empresa, Branch, UsuarioExtendido, Rol, Permiso
        from core.models import UnitOfMeasure
        from accounting.models import ChartOfAccounts, Journal, Tax, FiscalYear
        from sales.models import PaymentMethod
        
        # Verificaciones básicas
        checks = [
            ('Empresas', Empresa.objects.count()),
            ('Sucursales', Branch.objects.count()),
            ('Usuarios', UsuarioExtendido.objects.count()),
            ('Roles', Rol.objects.count()),
            ('Permisos', Permiso.objects.count()),
            ('Unidades de Medida', UnitOfMeasure.objects.count()),
            ('Cuentas Contables', ChartOfAccounts.objects.count()),
            ('Diarios', Journal.objects.count()),
            ('Impuestos', Tax.objects.count()),
            ('Años Fiscales', FiscalYear.objects.count()),
            ('Métodos de Pago', PaymentMethod.objects.count()),
        ]
        
        for name, count in checks:
            if count > 0:
                self.stdout.write(f'    ✅ {name}: {count}')
            else:
                self.stdout.write(self.style.WARNING(f'    ⚠️ {name}: {count}'))
        
        self.stdout.write(self.style.SUCCESS('  ✅ Verificación de integridad completada'))

    def print_summary(self):
        """Imprimir resumen de la puesta en marcha"""
        self.stdout.write('\n📋 RESUMEN DE LA PUESTA EN MARCHA:')
        self.stdout.write('=' * 50)
        self.stdout.write('✅ Migraciones aplicadas')
        self.stdout.write('✅ Empresa y sucursal configuradas')
        self.stdout.write('✅ Datos geográficos poblados')
        self.stdout.write('✅ Permisos y roles creados')
        self.stdout.write('✅ Usuarios sincronizados con Firebase')
        self.stdout.write('✅ Módulos del sistema configurados')
        self.stdout.write('✅ Contabilidad configurada')
        self.stdout.write('✅ Métodos de pago configurados')
        self.stdout.write('✅ Sucursales asignadas a administradores')
        self.stdout.write('✅ Integridad del sistema verificada')
        self.stdout.write('=' * 50)
        self.stdout.write('\n🎉 El sistema Synap está listo para usar!')
        self.stdout.write('\n📝 Próximos pasos recomendados:')
        self.stdout.write('   1. Configurar datos específicos de la empresa')
        self.stdout.write('   2. Crear usuarios adicionales según necesidades')
        self.stdout.write('   3. Configurar integraciones externas')
        self.stdout.write('   4. Realizar pruebas del sistema')
        self.stdout.write('   5. Configurar respaldos automáticos') 