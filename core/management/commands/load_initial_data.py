from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from core.models import Country, State, Currency, FiscalResponsibility, UnitOfMeasure, SystemConfiguration
from sales.models import PaymentMethod, PaymentTerm, PriceList
from inventory.models import Category, Brand
from accounting.models import TaxGroup, Tax, ChartOfAccounts, AccountTypes
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load complete initial data for Synap system including geographic, units, payment methods, categories, taxes, and system configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-geographic',
            action='store_true',
            help='Skip loading geographic data (countries, states, currencies, fiscal responsibilities)',
        )
        parser.add_argument(
            '--skip-units',
            action='store_true',
            help='Skip loading units of measure',
        )
        parser.add_argument(
            '--skip-payment-methods',
            action='store_true',
            help='Skip loading payment methods',
        )
        parser.add_argument(
            '--skip-categories',
            action='store_true',
            help='Skip loading categories and brands',
        )
        parser.add_argument(
            '--skip-taxes',
            action='store_true',
            help='Skip loading tax configuration',
        )
        parser.add_argument(
            '--skip-payment-terms',
            action='store_true',
            help='Skip loading payment terms',
        )
        parser.add_argument(
            '--skip-price-lists',
            action='store_true',
            help='Skip loading price lists',
        )
        parser.add_argument(
            '--skip-system-config',
            action='store_true',
            help='Skip loading system configuration',
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Loading complete initial data for Synap system...')
        
        with transaction.atomic():
            # 1. Datos geográficos
            if not options['skip_geographic']:
                self.create_geographic_data()
            
            # 2. Unidades de medida
            if not options['skip_units']:
                self.create_units_of_measure()
            
            # 3. Métodos de pago
            if not options['skip_payment_methods']:
                self.create_payment_methods()
            
            # 4. Categorías y marcas
            if not options['skip_categories']:
                self.create_categories_and_brands()
            
            # 5. Configuración de impuestos
            if not options['skip_taxes']:
                self.create_tax_configuration()
            
            # 6. Condiciones de pago
            if not options['skip_payment_terms']:
                self.create_payment_terms()
            
            # 7. Listas de precios
            if not options['skip_price_lists']:
                self.create_price_lists()
            
            # 8. Configuración del sistema
            if not options['skip_system_config']:
                self.create_system_configuration()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Complete initial data loaded successfully!')
        )

    def create_geographic_data(self):
        """Crear datos geográficos completos"""
        self.stdout.write('🌍 Loading geographic data...')
        
        # Crear países
        countries_data = [
            {
                'name': 'Argentina',
                'name_es': 'Argentina',
                'name_en': 'Argentina',
                'name_pt': 'Argentina',
                'code': 'ARG',
                'code_2': 'AR',
                'phone_code': '+54',
                'currency_code': 'ARS',
                'timezone': 'America/Argentina/Buenos_Aires',
            },
            {
                'name': 'Chile',
                'name_es': 'Chile',
                'name_en': 'Chile',
                'name_pt': 'Chile',
                'code': 'CHL',
                'code_2': 'CL',
                'phone_code': '+56',
                'currency_code': 'CLP',
                'timezone': 'America/Santiago',
            },
            {
                'name': 'Uruguay',
                'name_es': 'Uruguay',
                'name_en': 'Uruguay',
                'name_pt': 'Uruguai',
                'code': 'URY',
                'code_2': 'UY',
                'phone_code': '+598',
                'currency_code': 'UYU',
                'timezone': 'America/Montevideo',
            },
            {
                'name': 'Paraguay',
                'name_es': 'Paraguay',
                'name_en': 'Paraguay',
                'name_pt': 'Paraguai',
                'code': 'PRY',
                'code_2': 'PY',
                'phone_code': '+595',
                'currency_code': 'PYG',
                'timezone': 'America/Asuncion',
            },
            {
                'name': 'Brazil',
                'name_es': 'Brasil',
                'name_en': 'Brazil',
                'name_pt': 'Brasil',
                'code': 'BRA',
                'code_2': 'BR',
                'phone_code': '+55',
                'currency_code': 'BRL',
                'timezone': 'America/Sao_Paulo',
            },
            {
                'name': 'United States',
                'name_es': 'Estados Unidos',
                'name_en': 'United States',
                'name_pt': 'Estados Unidos',
                'code': 'USA',
                'code_2': 'US',
                'phone_code': '+1',
                'currency_code': 'USD',
                'timezone': 'America/New_York',
            },
            {
                'name': 'Spain',
                'name_es': 'España',
                'name_en': 'Spain',
                'name_pt': 'Espanha',
                'code': 'ESP',
                'code_2': 'ES',
                'phone_code': '+34',
                'currency_code': 'EUR',
                'timezone': 'Europe/Madrid',
            },
        ]
        
        created_countries = 0
        for country_data in countries_data:
            country, created = Country.objects.get_or_create(
                code=country_data['code'],
                defaults=country_data
            )
            if created:
                created_countries += 1
                self.stdout.write(f'  ✅ Created country: {country.name}')
        
        self.stdout.write(f'  📊 {created_countries} countries created/updated')
        
        # Crear monedas
        currencies_data = [
            {'code': 'ARS', 'name': 'Peso Argentino', 'symbol': '$'},
            {'code': 'CLP', 'name': 'Peso Chileno', 'symbol': '$'},
            {'code': 'UYU', 'name': 'Peso Uruguayo', 'symbol': '$'},
            {'code': 'PYG', 'name': 'Guaraní Paraguayo', 'symbol': '₲'},
            {'code': 'BRL', 'name': 'Real Brasileño', 'symbol': 'R$'},
            {'code': 'USD', 'name': 'Dólar Estadounidense', 'symbol': '$'},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
        ]
        
        created_currencies = 0
        for currency_data in currencies_data:
            currency, created = Currency.objects.get_or_create(
                code=currency_data['code'],
                defaults=currency_data
            )
            if created:
                created_currencies += 1
                self.stdout.write(f'  ✅ Created currency: {currency.name}')
        
        self.stdout.write(f'  💰 {created_currencies} currencies created/updated')
        
        # Crear responsabilidades fiscales
        created_responsibilities = 0
        for country_code, responsibilities in FiscalResponsibility.RESPONSIBILITY_TYPES.items():
            try:
                country = Country.objects.get(code=country_code)
                for code, name in responsibilities.items():
                    responsibility, created = FiscalResponsibility.objects.get_or_create(
                        code=code,
                        country=country,
                        defaults={
                            'name': name,
                            'description': f'Responsabilidad fiscal oficial de {country.name}',
                            'is_active': True
                        }
                    )
                    if created:
                        created_responsibilities += 1
            except Country.DoesNotExist:
                continue
        
        self.stdout.write(f'  🏛️ {created_responsibilities} fiscal responsibilities created/updated')
        
        # Crear estados/provincias (datos básicos)
        self.create_basic_states()
        
        self.stdout.write('  ✅ Geographic data loaded successfully')

    def create_basic_states(self):
        """Crear estados/provincias básicos para los países principales"""
        # Argentina - Provincias principales
        argentina = Country.objects.get(code='ARG')
        argentina_states = [
            {'name': 'Buenos Aires', 'code': 'BA'},
            {'name': 'Ciudad Autónoma de Buenos Aires', 'code': 'CABA'},
            {'name': 'Córdoba', 'code': 'COR'},
            {'name': 'Santa Fe', 'code': 'SFE'},
            {'name': 'Mendoza', 'code': 'MEN'},
            {'name': 'Tucumán', 'code': 'TUC'},
            {'name': 'Entre Ríos', 'code': 'ERI'},
            {'name': 'Salta', 'code': 'SAL'},
            {'name': 'Misiones', 'code': 'MIS'},
            {'name': 'Chaco', 'code': 'CHA'},
        ]
        
        created_states = 0
        for state_data in argentina_states:
            state, created = State.objects.get_or_create(
                country=argentina,
                name=state_data['name'],
                defaults=state_data
            )
            if created:
                created_states += 1
        
        self.stdout.write(f'  📍 {created_states} states/provinces created for Argentina')

    def create_units_of_measure(self):
        """Crear unidades de medida estándar"""
        self.stdout.write('📏 Loading units of measure...')
        
        # Unidades de cantidad
        quantity_units = [
            {'name': 'Unidad', 'code': 'un', 'category': 'quantity', 'ratio': 1, 'is_reference': True},
            {'name': 'Docena', 'code': 'doc', 'category': 'quantity', 'ratio': 12, 'is_reference': False},
            {'name': 'Centena', 'code': 'cen', 'category': 'quantity', 'ratio': 100, 'is_reference': False},
            {'name': 'Millar', 'code': 'mil', 'category': 'quantity', 'ratio': 1000, 'is_reference': False},
        ]
        
        # Unidades de peso (sistema métrico)
        weight_units = [
            {'name': 'Gramo', 'code': 'g', 'category': 'weight', 'ratio': 1, 'is_reference': True},
            {'name': 'Kilogramo', 'code': 'kg', 'category': 'weight', 'ratio': 1000, 'is_reference': False},
            {'name': 'Tonelada', 'code': 't', 'category': 'weight', 'ratio': 1000000, 'is_reference': False},
            {'name': 'Libra', 'code': 'lb', 'category': 'weight', 'ratio': 453.592, 'is_reference': False},
        ]
        
        # Unidades de volumen
        volume_units = [
            {'name': 'Litro', 'code': 'l', 'category': 'volume', 'ratio': 1, 'is_reference': True},
            {'name': 'Mililitro', 'code': 'ml', 'category': 'volume', 'ratio': 0.001, 'is_reference': False},
            {'name': 'Metro cúbico', 'code': 'm3', 'category': 'volume', 'ratio': 1000, 'is_reference': False},
        ]
        
        # Unidades de longitud
        length_units = [
            {'name': 'Metro', 'code': 'm', 'category': 'length', 'ratio': 1, 'is_reference': True},
            {'name': 'Centímetro', 'code': 'cm', 'category': 'length', 'ratio': 0.01, 'is_reference': False},
            {'name': 'Milímetro', 'code': 'mm', 'category': 'length', 'ratio': 0.001, 'is_reference': False},
            {'name': 'Kilómetro', 'code': 'km', 'category': 'length', 'ratio': 1000, 'is_reference': False},
        ]
        
        all_units = quantity_units + weight_units + volume_units + length_units
        
        created_units = 0
        for unit_data in all_units:
            unit, created = UnitOfMeasure.objects.get_or_create(
                code=unit_data['code'],
                defaults=unit_data
            )
            if created:
                created_units += 1
                self.stdout.write(f'  ✅ Created unit: {unit.name} ({unit.code})')
        
        self.stdout.write(f'  📏 {created_units} units of measure created/updated')

    def create_payment_methods(self):
        """Crear métodos de pago básicos"""
        self.stdout.write('💳 Loading payment methods...')
        
        # Obtener primera empresa para asignar métodos de pago
        from core.models import Empresa
        empresa = Empresa.objects.first()
        if not empresa:
            self.stdout.write('  ⚠️ No company found, skipping payment methods')
            return
        
        payment_methods_data = [
            {
                'name': 'Efectivo',
                'code': 'CASH',
                'payment_type': 'cash',
                'icon': 'payments',
                'color': '#10B981',
                'is_default': True,
                'order': 1,
                'empresa': empresa,
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
                    'requires_installments': True,
                    'max_installments': 12,
                    'empresa': empresa,
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
                'empresa': empresa,
            },
            {
                'name': 'Transferencia Bancaria',
                'code': 'BANK_TRANSFER',
                'payment_type': 'bank_transfer',
                'icon': 'account_balance',
                'color': '#059669',
                'order': 4,
                'requires_reference': True,
                'empresa': empresa,
            },
            {
                'name': 'MercadoPago',
                'code': 'MERCADOPAGO',
                'payment_type': 'digital_wallet',
                'icon': 'account_balance_wallet',
                'color': '#00A1E0',
                'order': 5,
                'processor_name': 'MercadoPago',
                'empresa': empresa,
            },
        ]
        
        created_methods = 0
        for method_data in payment_methods_data:
            method, created = PaymentMethod.objects.get_or_create(
                code=method_data['code'],
                empresa=method_data['empresa'],
                defaults=method_data
            )
            if created:
                created_methods += 1
                self.stdout.write(f'  ✅ Created payment method: {method.name}')
        
        self.stdout.write(f'  💳 {created_methods} payment methods created/updated')

    def create_categories_and_brands(self):
        """Crear categorías y marcas básicas"""
        self.stdout.write('🏷️ Loading categories and brands...')
        
        # Categorías básicas
        categories_data = [
            'Electrónicos',
            'Ropa y Accesorios',
            'Hogar y Jardín',
            'Deportes y Aire Libre',
            'Libros y Entretenimiento',
            'Salud y Belleza',
            'Juguetes y Juegos',
            'Automotriz',
            'Alimentos y Bebidas',
            'Herramientas y Construcción',
            'Mascotas',
            'Oficina y Papelería',
        ]
        
        created_categories = 0
        for category_name in categories_data:
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'is_active': True}
            )
            if created:
                created_categories += 1
                self.stdout.write(f'  ✅ Created category: {category.name}')
        
        self.stdout.write(f'  📂 {created_categories} categories created/updated')
        
        # Marcas básicas
        brands_data = [
            'Genérica',
            'Sin Marca',
            'Marca Propia',
        ]
        
        created_brands = 0
        for brand_name in brands_data:
            brand, created = Brand.objects.get_or_create(
                name=brand_name,
                defaults={'is_active': True}
            )
            if created:
                created_brands += 1
                self.stdout.write(f'  ✅ Created brand: {brand.name}')
        
        self.stdout.write(f'  🏭 {created_brands} brands created/updated')

    def create_tax_configuration(self):
        """Crear configuración de impuestos básica"""
        self.stdout.write('💰 Loading tax configuration...')
        
        # Obtener primera empresa
        from core.models import Empresa
        empresa = Empresa.objects.first()
        if not empresa:
            self.stdout.write('  ⚠️ No company found, skipping tax configuration')
            return
        
        # Crear plan de cuentas básico si no existe
        self.create_basic_chart_of_accounts(empresa)
        
        # Crear grupos de impuestos
        tax_groups_data = [
            {
                'name': 'IVA',
                'code': 'IVA',
                'description': 'Impuesto al Valor Agregado',
            },
            {
                'name': 'Impuestos Internos',
                'code': 'IIBB',
                'description': 'Impuestos Internos',
            },
            {
                'name': 'Percepciones',
                'code': 'PERC',
                'description': 'Percepciones de impuestos',
            },
        ]
        
        created_groups = 0
        for group_data in tax_groups_data:
            # Obtener cuenta de impuestos por defecto
            tax_account = ChartOfAccounts.objects.filter(
                empresa=empresa,
                name__icontains='impuesto'
            ).first()
            
            if not tax_account:
                # Crear cuenta de impuestos si no existe
                tax_account = ChartOfAccounts.objects.create(
                    empresa=empresa,
                    name='Impuestos por Pagar',
                    code='2201',
                    account_type=AccountTypes.LIABILITIES,
                    is_active=True
                )
            
            group, created = TaxGroup.objects.get_or_create(
                code=group_data['code'],
                empresa=empresa,
                defaults={
                    **group_data,
                    'account_id': tax_account,
                    'is_active': True
                }
            )
            if created:
                created_groups += 1
                self.stdout.write(f'  ✅ Created tax group: {group.name}')
        
        self.stdout.write(f'  💰 {created_groups} tax groups created/updated')

    def create_basic_chart_of_accounts(self, empresa):
        """Crear plan de cuentas básico"""
        accounts_data = [
            # Activos
            {'code': '1100', 'name': 'Caja y Bancos', 'account_type': AccountTypes.ASSETS},
            {'code': '1200', 'name': 'Cuentas por Cobrar', 'account_type': AccountTypes.ASSETS},
            {'code': '1300', 'name': 'Inventarios', 'account_type': AccountTypes.ASSETS},
            {'code': '1400', 'name': 'Activos Fijos', 'account_type': AccountTypes.ASSETS},
            
            # Pasivos
            {'code': '2100', 'name': 'Cuentas por Pagar', 'account_type': AccountTypes.LIABILITIES},
            {'code': '2200', 'name': 'Impuestos por Pagar', 'account_type': AccountTypes.LIABILITIES},
            {'code': '2300', 'name': 'Préstamos', 'account_type': AccountTypes.LIABILITIES},
            
            # Patrimonio
            {'code': '3100', 'name': 'Capital Social', 'account_type': AccountTypes.EQUITY},
            {'code': '3200', 'name': 'Utilidades Retenidas', 'account_type': AccountTypes.EQUITY},
            
            # Ingresos
            {'code': '4100', 'name': 'Ventas', 'account_type': AccountTypes.INCOME},
            {'code': '4200', 'name': 'Otros Ingresos', 'account_type': AccountTypes.INCOME},
            
            # Gastos
            {'code': '5100', 'name': 'Costo de Ventas', 'account_type': AccountTypes.EXPENSES},
            {'code': '5200', 'name': 'Gastos Administrativos', 'account_type': AccountTypes.EXPENSES},
            {'code': '5300', 'name': 'Gastos de Ventas', 'account_type': AccountTypes.EXPENSES},
        ]
        
        for account_data in accounts_data:
            ChartOfAccounts.objects.get_or_create(
                code=account_data['code'],
                empresa=empresa,
                defaults=account_data
            )

    def create_payment_terms(self):
        """Crear condiciones de pago básicas"""
        self.stdout.write('📅 Loading payment terms...')
        
        # Obtener primera empresa
        from core.models import Empresa
        empresa = Empresa.objects.first()
        if not empresa:
            self.stdout.write('  ⚠️ No company found, skipping payment terms')
            return
        
        payment_terms_data = [
            {
                'code': 'CONTADO',
                'name': 'Contado',
                'type': 'standard',
                'payment_days': 0,
                'description': 'Pago inmediato al momento de la venta',
                'empresa': empresa,
            },
            {
                'code': '15_DIAS',
                'name': '15 días',
                'type': 'standard',
                'payment_days': 15,
                'description': 'Pago a 15 días de la fecha de facturación',
                'empresa': empresa,
            },
            {
                'code': '30_DIAS',
                'name': '30 días',
                'type': 'standard',
                'payment_days': 30,
                'description': 'Pago a 30 días de la fecha de facturación',
                'empresa': empresa,
            },
            {
                'code': '60_DIAS',
                'name': '60 días',
                'type': 'standard',
                'payment_days': 60,
                'description': 'Pago a 60 días de la fecha de facturación',
                'empresa': empresa,
            },
            {
                'code': '90_DIAS',
                'name': '90 días',
                'type': 'standard',
                'payment_days': 90,
                'description': 'Pago a 90 días de la fecha de facturación',
                'empresa': empresa,
            },
        ]
        
        created_terms = 0
        for term_data in payment_terms_data:
            term, created = PaymentTerm.objects.get_or_create(
                code=term_data['code'],
                empresa=term_data['empresa'],
                defaults=term_data
            )
            if created:
                created_terms += 1
                self.stdout.write(f'  ✅ Created payment term: {term.name}')
        
        self.stdout.write(f'  📅 {created_terms} payment terms created/updated')

    def create_system_configuration(self):
        """Crear configuración del sistema por defecto"""
        self.stdout.write('⚙️ Loading system configuration...')
        
        config_data = [
            {
                'key': 'system.company.name',
                'value': 'Synap System',
                'description': 'Nombre por defecto de la empresa del sistema',
            },
            {
                'key': 'system.default.language',
                'value': 'es',
                'description': 'Idioma por defecto del sistema',
            },
            {
                'key': 'system.default.timezone',
                'value': 'America/Argentina/Buenos_Aires',
                'description': 'Zona horaria por defecto',
            },
            {
                'key': 'system.default.currency',
                'value': 'ARS',
                'description': 'Moneda por defecto del sistema',
            },
            {
                'key': 'system.date.format',
                'value': 'DD/MM/YYYY',
                'description': 'Formato de fecha por defecto',
            },
            {
                'key': 'system.decimal.separator',
                'value': ',',
                'description': 'Separador decimal por defecto',
            },
            {
                'key': 'system.thousands.separator',
                'value': '.',
                'description': 'Separador de miles por defecto',
            },
            {
                'key': 'system.inventory.negative.stock',
                'value': 'false',
                'description': 'Permitir stock negativo',
            },
            {
                'key': 'system.sales.require.customer',
                'value': 'true',
                'description': 'Requerir cliente en ventas',
            },
            {
                'key': 'system.accounting.auto.post',
                'value': 'false',
                'description': 'Publicar asientos automáticamente',
            },
        ]
        
        created_configs = 0
        for config_item in config_data:
            config, created = SystemConfiguration.objects.get_or_create(
                key=config_item['key'],
                defaults=config_item
            )
            if created:
                created_configs += 1
                self.stdout.write(f'  ✅ Created config: {config.key}')
        
        self.stdout.write(f'  ⚙️ {created_configs} system configurations created/updated') 

    def create_price_lists(self):
        """Crear lista de precios predeterminada"""
        self.stdout.write('💰 Loading price lists...')
        
        # Obtener primera empresa
        from core.models import Empresa
        empresa = Empresa.objects.first()
        if not empresa:
            self.stdout.write('  ⚠️ No company found, skipping price lists')
            return
        
        # Obtener moneda por defecto (ARS para Argentina)
        default_currency = 'ARS'
        
        # Crear lista de precios predeterminada
        price_list, created = PriceList.objects.get_or_create(
            name='Lista de precios predeterminada',
            defaults={
                'currency': default_currency,
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(f'  ✅ Created price list: {price_list.name}')
        else:
            self.stdout.write(f'  ℹ️ Price list already exists: {price_list.name}')
        
        self.stdout.write(f'  💰 1 price list created/updated') 