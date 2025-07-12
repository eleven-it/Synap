from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Empresa
from accounting.models import ChartOfAccounts, AccountTypes
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup sample chart of accounts for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID of the company to setup accounts for',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of accounts even if they exist',
        )

    def handle(self, *args, **options):
        empresa_id = options['empresa_id']
        force = options['force']

        # Obtener empresa
        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa with ID {empresa_id} does not exist.')
                )
                return
        else:
            # Usar la primera empresa disponible
            empresa = Empresa.objects.first()
            if not empresa:
                self.stdout.write(
                    self.style.ERROR('No companies found. Please create a company first.')
                )
                return

        self.stdout.write(
            self.style.SUCCESS(f'Setting up chart of accounts for: {empresa.nombre}')
        )

        # Verificar si ya existen cuentas
        existing_accounts = ChartOfAccounts.objects.filter(empresa=empresa).count()
        if existing_accounts > 0 and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {existing_accounts} existing accounts. Use --force to recreate them.'
                )
            )
            return

        if force:
            # Verificar si hay cuentas referenciadas por otros modelos
            referenced_accounts = ChartOfAccounts.objects.filter(empresa=empresa)
            if referenced_accounts.exists():
                self.stdout.write(
                    self.style.WARNING(
                        'Some accounts are referenced by other models (taxes, journals, etc.). '
                        'Skipping deletion to avoid data integrity issues.'
                    )
                )
                force = False
            else:
                # Eliminar cuentas existentes
                ChartOfAccounts.objects.filter(empresa=empresa).delete()
                self.stdout.write('Deleted existing accounts.')

        # Crear cuentas padre (nivel raíz)
        accounts_data = [
            # Assets (Activos)
            {
                'code': '1000',
                'name': 'Assets',
                'account_type': AccountTypes.ASSETS,
                'parent': None,
            },
            # Liabilities (Pasivos)
            {
                'code': '2000',
                'name': 'Liabilities',
                'account_type': AccountTypes.LIABILITIES,
                'parent': None,
            },
            # Equity (Patrimonio)
            {
                'code': '3000',
                'name': 'Equity',
                'account_type': AccountTypes.EQUITY,
                'parent': None,
            },
            # Income (Ingresos)
            {
                'code': '4000',
                'name': 'Income',
                'account_type': AccountTypes.INCOME,
                'parent': None,
            },
            # Expenses (Gastos)
            {
                'code': '5000',
                'name': 'Expenses',
                'account_type': AccountTypes.EXPENSES,
                'parent': None,
            },
        ]

        # Crear cuentas padre
        parent_accounts = {}
        for data in accounts_data:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=data['account_type'],
                parent=data['parent'],
                is_active=True,
            )
            parent_accounts[data['code']] = account
            self.stdout.write(f'Created parent account: {account.code} - {account.name}')

        # Crear subcuentas de Activos
        assets_subaccounts = [
            {'code': '1100', 'name': 'Current Assets', 'parent': '1000'},
            {'code': '1200', 'name': 'Fixed Assets', 'parent': '1000'},
            {'code': '1300', 'name': 'Intangible Assets', 'parent': '1000'},
        ]

        for data in assets_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.ASSETS,
                parent=parent_accounts[data['parent']],
                is_active=True,
            )
            self.stdout.write(f'Created subaccount: {account.code} - {account.name}')

        # Crear cuentas específicas de Activos Corrientes
        current_assets = ChartOfAccounts.objects.get(code='1100', empresa=empresa)
        current_assets_subaccounts = [
            {'code': '1110', 'name': 'Cash and Cash Equivalents'},
            {'code': '1120', 'name': 'Accounts Receivable'},
            {'code': '1130', 'name': 'Inventory'},
            {'code': '1140', 'name': 'Prepaid Expenses'},
        ]

        for data in current_assets_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.ASSETS,
                parent=current_assets,
                is_active=True,
            )
            self.stdout.write(f'Created account: {account.code} - {account.name}')

        # Crear subcuentas de Pasivos
        liabilities_subaccounts = [
            {'code': '2100', 'name': 'Current Liabilities', 'parent': '2000'},
            {'code': '2200', 'name': 'Long-term Liabilities', 'parent': '2000'},
        ]

        for data in liabilities_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.LIABILITIES,
                parent=parent_accounts[data['parent']],
                is_active=True,
            )
            self.stdout.write(f'Created subaccount: {account.code} - {account.name}')

        # Crear cuentas específicas de Pasivos Corrientes
        current_liabilities = ChartOfAccounts.objects.get(code='2100', empresa=empresa)
        current_liabilities_subaccounts = [
            {'code': '2110', 'name': 'Accounts Payable'},
            {'code': '2120', 'name': 'Accrued Expenses'},
            {'code': '2130', 'name': 'Short-term Loans'},
        ]

        for data in current_liabilities_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.LIABILITIES,
                parent=current_liabilities,
                is_active=True,
            )
            self.stdout.write(f'Created account: {account.code} - {account.name}')

        # Crear subcuentas de Patrimonio
        equity_subaccounts = [
            {'code': '3100', 'name': 'Capital', 'parent': '3000'},
            {'code': '3200', 'name': 'Retained Earnings', 'parent': '3000'},
        ]

        for data in equity_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.EQUITY,
                parent=parent_accounts[data['parent']],
                is_active=True,
            )
            self.stdout.write(f'Created subaccount: {account.code} - {account.name}')

        # Crear subcuentas de Ingresos
        income_subaccounts = [
            {'code': '4100', 'name': 'Sales Revenue', 'parent': '4000'},
            {'code': '4200', 'name': 'Other Income', 'parent': '4000'},
        ]

        for data in income_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.INCOME,
                parent=parent_accounts[data['parent']],
                is_active=True,
            )
            self.stdout.write(f'Created subaccount: {account.code} - {account.name}')

        # Crear cuentas específicas de Ventas
        sales_revenue = ChartOfAccounts.objects.get(code='4100', empresa=empresa)
        sales_subaccounts = [
            {'code': '4110', 'name': 'Product Sales'},
            {'code': '4120', 'name': 'Service Sales'},
        ]

        for data in sales_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.INCOME,
                parent=sales_revenue,
                is_active=True,
            )
            self.stdout.write(f'Created account: {account.code} - {account.name}')

        # Crear subcuentas de Gastos
        expenses_subaccounts = [
            {'code': '5100', 'name': 'Cost of Goods Sold', 'parent': '5000'},
            {'code': '5200', 'name': 'Operating Expenses', 'parent': '5000'},
            {'code': '5300', 'name': 'Financial Expenses', 'parent': '5000'},
        ]

        for data in expenses_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.EXPENSES,
                parent=parent_accounts[data['parent']],
                is_active=True,
            )
            self.stdout.write(f'Created subaccount: {account.code} - {account.name}')

        # Crear cuentas específicas de Gastos Operativos
        operating_expenses = ChartOfAccounts.objects.get(code='5200', empresa=empresa)
        operating_expenses_subaccounts = [
            {'code': '5210', 'name': 'Salaries and Wages'},
            {'code': '5220', 'name': 'Rent Expense'},
            {'code': '5230', 'name': 'Utilities'},
            {'code': '5240', 'name': 'Office Supplies'},
            {'code': '5250', 'name': 'Marketing and Advertising'},
        ]

        for data in operating_expenses_subaccounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=AccountTypes.EXPENSES,
                parent=operating_expenses,
                is_active=True,
            )
            self.stdout.write(f'Created account: {account.code} - {account.name}')

        # Crear algunas cuentas de impuestos
        tax_accounts = [
            {
                'code': '2160',
                'name': 'VAT Payable',
                'account_type': AccountTypes.LIABILITIES,
                'parent': current_liabilities,
                'is_tax_account': True,
                'tax_type': 'VAT',
            },
            {
                'code': '2170',
                'name': 'Income Tax Payable',
                'account_type': AccountTypes.LIABILITIES,
                'parent': current_liabilities,
                'is_tax_account': True,
                'tax_type': 'Income Tax',
            },
            {
                'code': '1180',
                'name': 'VAT Receivable',
                'account_type': AccountTypes.ASSETS,
                'parent': current_assets,
                'is_tax_account': True,
                'tax_type': 'VAT',
            },
        ]

        for data in tax_accounts:
            account = ChartOfAccounts.objects.create(
                empresa=empresa,
                code=data['code'],
                name=data['name'],
                account_type=data['account_type'],
                parent=data['parent'],
                is_active=True,
                is_tax_account=data['is_tax_account'],
                tax_type=data['tax_type'],
            )
            self.stdout.write(f'Created tax account: {account.code} - {account.name}')

        total_accounts = ChartOfAccounts.objects.filter(empresa=empresa).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {total_accounts} accounts for {empresa.nombre}'
            )
        ) 