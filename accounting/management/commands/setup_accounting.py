from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Empresa
from accounting.models import (
    ChartOfAccounts, Journal, AccountTypes, JournalTypes,
    TaxGroup, Tax, EntryStates
)
from decimal import Decimal


class Command(BaseCommand):
    help = 'Configurar contabilidad inicial para una empresa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de la empresa para configurar',
        )
        parser.add_argument(
            '--empresa-nombre',
            type=str,
            help='Nombre de la empresa para configurar',
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        empresa_nombre = options.get('empresa_nombre')

        # Obtener empresa
        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa con ID {empresa_id} no encontrada')
                )
                return
        elif empresa_nombre:
            try:
                empresa = Empresa.objects.get(nombre=empresa_nombre)
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa "{empresa_nombre}" no encontrada')
                )
                return
        else:
            # Usar primera empresa disponible
            empresa = Empresa.objects.first()
            if not empresa:
                self.stdout.write(
                    self.style.ERROR('No hay empresas configuradas')
                )
                return

        self.stdout.write(
            self.style.SUCCESS(f'Configurando contabilidad para: {empresa.nombre}')
        )

        with transaction.atomic():
            # 1. Crear plan de cuentas básico
            self._create_chart_of_accounts(empresa)
            
            # 2. Crear diarios contables
            self._create_journals(empresa)
            
            # 3. Crear grupos de impuestos básicos
            self._create_tax_groups(empresa)
            
            # 4. Crear impuestos básicos
            self._create_basic_taxes(empresa)

        self.stdout.write(
            self.style.SUCCESS('Configuración de contabilidad completada exitosamente')
        )

    def _create_chart_of_accounts(self, empresa):
        """Crear plan de cuentas básico"""
        self.stdout.write('Creando plan de cuentas...')

        # Cuentas principales
        accounts_data = [
            # Activos
            ('1100', 'Caja y Bancos', AccountTypes.ASSETS),
            ('1200', 'Cuentas por Cobrar', AccountTypes.ASSETS),
            ('1300', 'Inventarios', AccountTypes.ASSETS),
            ('1400', 'Activos Fijos', AccountTypes.ASSETS),
            
            # Pasivos
            ('2100', 'Cuentas por Pagar', AccountTypes.LIABILITIES),
            ('2200', 'Impuestos por Pagar', AccountTypes.LIABILITIES),
            ('2300', 'Préstamos', AccountTypes.LIABILITIES),
            
            # Patrimonio
            ('3100', 'Capital Social', AccountTypes.EQUITY),
            ('3200', 'Utilidades Retenidas', AccountTypes.EQUITY),
            
            # Ingresos
            ('4100', 'Ventas', AccountTypes.INCOME),
            ('4200', 'Otros Ingresos', AccountTypes.INCOME),
            
            # Gastos
            ('5100', 'Costo de Ventas', AccountTypes.EXPENSES),
            ('5200', 'Gastos Administrativos', AccountTypes.EXPENSES),
            ('5300', 'Gastos de Ventas', AccountTypes.EXPENSES),
        ]

        for code, name, account_type in accounts_data:
            account, created = ChartOfAccounts.objects.get_or_create(
                empresa=empresa,
                code=code,
                defaults={
                    'name': name,
                    'account_type': account_type,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Creada cuenta: {code} - {name}')
            else:
                self.stdout.write(f'  - Cuenta existente: {code} - {name}')

        # Cuentas específicas para impuestos
        tax_accounts = [
            ('2210', 'IVA Ventas', AccountTypes.LIABILITIES, True, 'IVA'),
            ('2220', 'IVA Compras', AccountTypes.LIABILITIES, True, 'IVA'),
            ('2230', 'Impuestos Internos', AccountTypes.LIABILITIES, True, 'INTERNOS'),
            ('2240', 'Percepciones', AccountTypes.LIABILITIES, True, 'PERCEPCIONES'),
        ]

        for code, name, account_type, is_tax, tax_type in tax_accounts:
            account, created = ChartOfAccounts.objects.get_or_create(
                empresa=empresa,
                code=code,
                defaults={
                    'name': name,
                    'account_type': account_type,
                    'is_active': True,
                    'is_tax_account': is_tax,
                    'tax_type': tax_type
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Creada cuenta de impuesto: {code} - {name}')

    def _create_journals(self, empresa):
        """Crear diarios contables básicos"""
        self.stdout.write('Creando diarios contables...')

        # Obtener cuentas necesarias
        caja_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='1100'
        ).first()
        
        ventas_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='4100'
        ).first()
        
        compras_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='5100'
        ).first()

        journals_data = [
            ('VENTAS', 'Diario de Ventas', JournalTypes.SALE, ventas_account),
            ('COMPRAS', 'Diario de Compras', JournalTypes.PURCHASE, compras_account),
            ('CAJA', 'Diario de Caja', JournalTypes.CASH, caja_account),
            ('BANCO', 'Diario de Banco', JournalTypes.BANK, caja_account),
            ('VARIOS', 'Diario Varios', JournalTypes.MISCELLANEOUS, None),
        ]

        for code, name, journal_type, default_account in journals_data:
            journal, created = Journal.objects.get_or_create(
                empresa=empresa,
                code=code,
                defaults={
                    'name': name,
                    'journal_type': journal_type,
                    'default_account': default_account,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Creado diario: {code} - {name}')
            else:
                self.stdout.write(f'  - Diario existente: {code} - {name}')

    def _create_tax_groups(self, empresa):
        """Crear grupos de impuestos básicos"""
        self.stdout.write('Creando grupos de impuestos...')

        # Obtener cuentas de impuestos
        iva_ventas_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='2210'
        ).first()
        
        iva_compras_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='2220'
        ).first()
        
        internos_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='2230'
        ).first()

        groups_data = [
            ('IVA', 'Impuesto al Valor Agregado', iva_ventas_account, iva_compras_account),
            ('INTERNOS', 'Impuestos Internos', internos_account, internos_account),
        ]

        for code, name, sales_account, purchase_account in groups_data:
            group, created = TaxGroup.objects.get_or_create(
                empresa=empresa,
                code=code,
                defaults={
                    'name': name,
                    'account_id': sales_account,
                    'refund_account_id': purchase_account,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Creado grupo: {code} - {name}')
            else:
                self.stdout.write(f'  - Grupo existente: {code} - {name}')

    def _create_basic_taxes(self, empresa):
        """Crear impuestos básicos"""
        self.stdout.write('Creando impuestos básicos...')

        # Obtener grupos de impuestos
        iva_group = TaxGroup.objects.filter(
            empresa=empresa, code='IVA'
        ).first()
        
        internos_group = TaxGroup.objects.filter(
            empresa=empresa, code='INTERNOS'
        ).first()

        # Obtener cuentas
        iva_ventas_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='2210'
        ).first()
        
        iva_compras_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='2220'
        ).first()
        
        internos_account = ChartOfAccounts.objects.filter(
            empresa=empresa, code='2230'
        ).first()

        taxes_data = [
            # IVA
            ('IVA21', 'IVA 21%', Decimal('21.00'), iva_group, iva_ventas_account, iva_compras_account),
            ('IVA10.5', 'IVA 10.5%', Decimal('10.50'), iva_group, iva_ventas_account, iva_compras_account),
            ('IVA27', 'IVA 27%', Decimal('27.00'), iva_group, iva_ventas_account, iva_compras_account),
            ('IVA0', 'IVA 0%', Decimal('0.00'), iva_group, iva_ventas_account, iva_compras_account),
            
            # Impuestos Internos
            ('IIBB', 'Impuestos Internos', Decimal('3.00'), internos_group, internos_account, internos_account),
        ]

        for code, name, amount, group, sales_account, purchase_account in taxes_data:
            tax, created = Tax.objects.get_or_create(
                empresa=empresa,
                code=code,
                defaults={
                    'name': name,
                    'amount': amount,
                    'amount_type': 'percent',
                    'tax_group': group,
                    'account_id': sales_account,
                    'refund_account_id': purchase_account,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Creado impuesto: {code} - {name} ({amount}%)')
            else:
                self.stdout.write(f'  - Impuesto existente: {code} - {name}') 