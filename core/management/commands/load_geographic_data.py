from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from core.models import Country, State
from core.models.currency import Currency
from core.models.fiscal_responsibility import FiscalResponsibility


class Command(BaseCommand):
    help = 'Load complete geographic data for Argentina, Chile, Uruguay, Paraguay, Brazil, United States and Spain'

    def handle(self, *args, **options):
        self.stdout.write('🌍 Loading geographic data...')
        
        # Crear países
        self.create_countries()
        
        # Crear monedas
        self.create_currencies()
        
        # Crear responsabilidades fiscales
        self.create_fiscal_responsibilities()
        
        # Crear estados/provincias
        self.create_states()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Geographic data loaded successfully!')
        )

    def create_countries(self):
        """Crear países principales"""
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

    def create_currencies(self):
        """Crear monedas para cada país"""
        currencies_data = [
            {
                'code': 'ARS',
                'name': 'Argentine Peso',
                'symbol': '$',
            },
            {
                'code': 'CLP',
                'name': 'Chilean Peso',
                'symbol': '$',
            },
            {
                'code': 'UYU',
                'name': 'Uruguayan Peso',
                'symbol': '$',
            },
            {
                'code': 'PYG',
                'name': 'Paraguayan Guaraní',
                'symbol': '₲',
            },
            {
                'code': 'BRL',
                'name': 'Brazilian Real',
                'symbol': 'R$',
            },
            {
                'code': 'USD',
                'name': 'US Dollar',
                'symbol': '$',
            },
            {
                'code': 'EUR',
                'name': 'Euro',
                'symbol': '€',
            },
        ]
        
        created_currencies = 0
        for currency_data in currencies_data:
            currency, created = Currency.objects.get_or_create(
                code=currency_data['code'],
                defaults=currency_data
            )
            if created:
                created_currencies += 1
                self.stdout.write(f'  ✅ Created currency: {currency.name} ({currency.code})')
        
        self.stdout.write(f'  📊 {created_currencies} currencies created/updated')

    def create_fiscal_responsibilities(self):
        """Crear responsabilidades fiscales oficiales para cada país"""
        responsibilities_data = {
            'ARG': {  # Argentina (AFIP)
                'RI': 'Responsable Inscripto',
                'RM': 'Responsable Monotributista', 
                'CF': 'Consumidor Final',
                'EX': 'Exento',
                'NR': 'No Responsable',
                'RNI': 'Responsable No Inscripto',
                'SR': 'Sujeto a Retención',
                'SP': 'Sujeto a Percepción',
                'RIVA': 'Responsable IVA Agropecuario',
                'PCE': 'Pequeño Contribuyente Eventual',
            },
            'CHL': {  # Chile (SII)
                'RPG': 'Régimen Pro Pyme General',
                'RPT': 'Régimen Pro Pyme Transparente',
                'RG': 'Régimen General (Artículo 14 A)',
                'RRP': 'Régimen de Renta Presunta',
                'RRA': 'Régimen de Renta Atribuida',
                'CSC': 'Contribuyente de Segunda Categoría',
                'EX': 'Exento',
            },
            'URY': {  # Uruguay (DGI)
                'RG': 'Régimen General',
                'RM': 'Régimen de Monotributo',
                'RPE': 'Régimen de Pequeños Empresarios',
                'EX': 'Exento',
                'CF': 'Consumidor Final',
            },
            'PRY': {  # Paraguay (SET)
                'RG': 'Régimen General',
                'RM': 'Régimen de Microempresa',
                'RPE': 'Régimen de Pequeños Empresarios',
                'EX': 'Exento',
                'CF': 'Consumidor Final',
            },
            'BRA': {  # Brasil (Receita Federal)
                'PJ': 'Pessoa Jurídica',
                'PF': 'Pessoa Física',
                'MEI': 'Microempreendedor Individual',
                'SN': 'Simples Nacional',
                'LP': 'Lucro Presumido',
                'LR': 'Lucro Real',
                'EX': 'Isento',
            },
            'USA': {  # USA (IRS)
                'IND': 'Individual',
                'CORP': 'Corporation',
                'LLC': 'Limited Liability Company',
                'PART': 'Partnership',
                'S_CORP': 'S Corporation',
                'TRUST': 'Trust',
                'ESTATE': 'Estate',
                'NON_PROFIT': 'Non-Profit Organization',
                'EXEMPT': 'Tax Exempt',
            },
            'ESP': {  # España (AEAT)
                'RG': 'Régimen General',
                'RA': 'Régimen de Autónomos',
                'RS': 'Régimen Simplificado',
                'RE': 'Régimen Especial',
                'EX': 'Exento',
                'CF': 'Consumidor Final',
            }
        }
        
        created_responsibilities = 0
        for country_code, responsibilities in responsibilities_data.items():
            try:
                country = Country.objects.get(code=country_code)
                country_created = 0
                
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
                        country_created += 1
                        created_responsibilities += 1
                
                self.stdout.write(f'  ✅ {country.name}: {country_created} fiscal responsibilities created')
                
            except Country.DoesNotExist:
                self.stdout.write(f'  ⚠️  Country {country_code} not found, skipping fiscal responsibilities')
        
        self.stdout.write(f'  📊 Total: {created_responsibilities} fiscal responsibilities created')

    def create_states(self):
        """Crear estados/provincias para cada país"""
        
        # Argentina - Todas las provincias
        argentina = Country.objects.get(code='ARG')
        argentina_states = [
            {'code': 'BA', 'name': 'Buenos Aires', 'name_es': 'Buenos Aires'},
            {'code': 'CABA', 'name': 'Ciudad Autónoma de Buenos Aires', 'name_es': 'Ciudad Autónoma de Buenos Aires'},
            {'code': 'CAT', 'name': 'Catamarca', 'name_es': 'Catamarca'},
            {'code': 'CHA', 'name': 'Chaco', 'name_es': 'Chaco'},
            {'code': 'CHU', 'name': 'Chubut', 'name_es': 'Chubut'},
            {'code': 'COR', 'name': 'Córdoba', 'name_es': 'Córdoba'},
            {'code': 'ERI', 'name': 'Entre Ríos', 'name_es': 'Entre Ríos'},
            {'code': 'FOR', 'name': 'Formosa', 'name_es': 'Formosa'},
            {'code': 'JUJ', 'name': 'Jujuy', 'name_es': 'Jujuy'},
            {'code': 'LAP', 'name': 'La Pampa', 'name_es': 'La Pampa'},
            {'code': 'LAR', 'name': 'La Rioja', 'name_es': 'La Rioja'},
            {'code': 'MEN', 'name': 'Mendoza', 'name_es': 'Mendoza'},
            {'code': 'MIS', 'name': 'Misiones', 'name_es': 'Misiones'},
            {'code': 'NEU', 'name': 'Neuquén', 'name_es': 'Neuquén'},
            {'code': 'RNE', 'name': 'Río Negro', 'name_es': 'Río Negro'},
            {'code': 'SAL', 'name': 'Salta', 'name_es': 'Salta'},
            {'code': 'SJU', 'name': 'San Juan', 'name_es': 'San Juan'},
            {'code': 'SLU', 'name': 'San Luis', 'name_es': 'San Luis'},
            {'code': 'SDE', 'name': 'Santiago del Estero', 'name_es': 'Santiago del Estero'},
            {'code': 'SFE', 'name': 'Santa Fe', 'name_es': 'Santa Fe'},
            {'code': 'TDF', 'name': 'Tierra del Fuego', 'name_es': 'Tierra del Fuego'},
            {'code': 'TUC', 'name': 'Tucumán', 'name_es': 'Tucumán'},
        ]
        
        # Chile - Todas las regiones
        chile = Country.objects.get(code='CHL')
        chile_states = [
            {'code': 'AR', 'name': 'Arica y Parinacota', 'name_es': 'Arica y Parinacota'},
            {'code': 'TA', 'name': 'Tarapacá', 'name_es': 'Tarapacá'},
            {'code': 'AN', 'name': 'Antofagasta', 'name_es': 'Antofagasta'},
            {'code': 'AT', 'name': 'Atacama', 'name_es': 'Atacama'},
            {'code': 'CO', 'name': 'Coquimbo', 'name_es': 'Coquimbo'},
            {'code': 'VA', 'name': 'Valparaíso', 'name_es': 'Valparaíso'},
            {'code': 'RM', 'name': 'Región Metropolitana de Santiago', 'name_es': 'Región Metropolitana de Santiago'},
            {'code': 'LI', 'name': 'Libertador General Bernardo O\'Higgins', 'name_es': 'Libertador General Bernardo O\'Higgins'},
            {'code': 'ML', 'name': 'Maule', 'name_es': 'Maule'},
            {'code': 'BI', 'name': 'Biobío', 'name_es': 'Biobío'},
            {'code': 'LA', 'name': 'La Araucanía', 'name_es': 'La Araucanía'},
            {'code': 'LR', 'name': 'Los Ríos', 'name_es': 'Los Ríos'},
            {'code': 'LL', 'name': 'Los Lagos', 'name_es': 'Los Lagos'},
            {'code': 'AI', 'name': 'Aysén del General Carlos Ibáñez del Campo', 'name_es': 'Aysén del General Carlos Ibáñez del Campo'},
            {'code': 'MA', 'name': 'Magallanes y de la Antártica Chilena', 'name_es': 'Magallanes y de la Antártica Chilena'},
            {'code': 'NB', 'name': 'Ñuble', 'name_es': 'Ñuble'},
        ]
        
        # Uruguay - Todos los departamentos
        uruguay = Country.objects.get(code='URY')
        uruguay_states = [
            {'code': 'AR', 'name': 'Artigas', 'name_es': 'Artigas'},
            {'code': 'CA', 'name': 'Canelones', 'name_es': 'Canelones'},
            {'code': 'CL', 'name': 'Cerro Largo', 'name_es': 'Cerro Largo'},
            {'code': 'CO', 'name': 'Colonia', 'name_es': 'Colonia'},
            {'code': 'DU', 'name': 'Durazno', 'name_es': 'Durazno'},
            {'code': 'FS', 'name': 'Flores', 'name_es': 'Flores'},
            {'code': 'FD', 'name': 'Florida', 'name_es': 'Florida'},
            {'code': 'LA', 'name': 'Lavalleja', 'name_es': 'Lavalleja'},
            {'code': 'MA', 'name': 'Maldonado', 'name_es': 'Maldonado'},
            {'code': 'MO', 'name': 'Montevideo', 'name_es': 'Montevideo'},
            {'code': 'PA', 'name': 'Paysandú', 'name_es': 'Paysandú'},
            {'code': 'RN', 'name': 'Río Negro', 'name_es': 'Río Negro'},
            {'code': 'RV', 'name': 'Rivera', 'name_es': 'Rivera'},
            {'code': 'RO', 'name': 'Rocha', 'name_es': 'Rocha'},
            {'code': 'SA', 'name': 'Salto', 'name_es': 'Salto'},
            {'code': 'SJ', 'name': 'San José', 'name_es': 'San José'},
            {'code': 'SO', 'name': 'Soriano', 'name_es': 'Soriano'},
            {'code': 'TA', 'name': 'Tacuarembó', 'name_es': 'Tacuarembó'},
            {'code': 'TT', 'name': 'Treinta y Tres', 'name_es': 'Treinta y Tres'},
        ]
        
        # Paraguay - Todos los departamentos
        paraguay = Country.objects.get(code='PRY')
        paraguay_states = [
            {'code': 'AL', 'name': 'Alto Paraguay', 'name_es': 'Alto Paraguay'},
            {'code': 'AN', 'name': 'Alto Paraná', 'name_es': 'Alto Paraná'},
            {'code': 'AM', 'name': 'Amambay', 'name_es': 'Amambay'},
            {'code': 'AS', 'name': 'Asunción', 'name_es': 'Asunción'},
            {'code': 'BO', 'name': 'Boquerón', 'name_es': 'Boquerón'},
            {'code': 'CA', 'name': 'Caaguazú', 'name_es': 'Caaguazú'},
            {'code': 'CG', 'name': 'Caazapá', 'name_es': 'Caazapá'},
            {'code': 'CN', 'name': 'Canindeyú', 'name_es': 'Canindeyú'},
            {'code': 'CE', 'name': 'Central', 'name_es': 'Central'},
            {'code': 'CO', 'name': 'Concepción', 'name_es': 'Concepción'},
            {'code': 'CD', 'name': 'Cordillera', 'name_es': 'Cordillera'},
            {'code': 'GU', 'name': 'Guairá', 'name_es': 'Guairá'},
            {'code': 'IT', 'name': 'Itapúa', 'name_es': 'Itapúa'},
            {'code': 'MI', 'name': 'Misiones', 'name_es': 'Misiones'},
            {'code': 'NE', 'name': 'Ñeembucú', 'name_es': 'Ñeembucú'},
            {'code': 'PA', 'name': 'Paraguarí', 'name_es': 'Paraguarí'},
            {'code': 'PH', 'name': 'Presidente Hayes', 'name_es': 'Presidente Hayes'},
            {'code': 'SP', 'name': 'San Pedro', 'name_es': 'San Pedro'},
        ]
        
        # Brasil - Todos los estados
        brazil = Country.objects.get(code='BRA')
        brazil_states = [
            {'code': 'AC', 'name': 'Acre', 'name_pt': 'Acre'},
            {'code': 'AL', 'name': 'Alagoas', 'name_pt': 'Alagoas'},
            {'code': 'AP', 'name': 'Amapá', 'name_pt': 'Amapá'},
            {'code': 'AM', 'name': 'Amazonas', 'name_pt': 'Amazonas'},
            {'code': 'BA', 'name': 'Bahia', 'name_pt': 'Bahia'},
            {'code': 'CE', 'name': 'Ceará', 'name_pt': 'Ceará'},
            {'code': 'DF', 'name': 'Distrito Federal', 'name_pt': 'Distrito Federal'},
            {'code': 'ES', 'name': 'Espírito Santo', 'name_pt': 'Espírito Santo'},
            {'code': 'GO', 'name': 'Goiás', 'name_pt': 'Goiás'},
            {'code': 'MA', 'name': 'Maranhão', 'name_pt': 'Maranhão'},
            {'code': 'MT', 'name': 'Mato Grosso', 'name_pt': 'Mato Grosso'},
            {'code': 'MS', 'name': 'Mato Grosso do Sul', 'name_pt': 'Mato Grosso do Sul'},
            {'code': 'MG', 'name': 'Minas Gerais', 'name_pt': 'Minas Gerais'},
            {'code': 'PA', 'name': 'Pará', 'name_pt': 'Pará'},
            {'code': 'PB', 'name': 'Paraíba', 'name_pt': 'Paraíba'},
            {'code': 'PR', 'name': 'Paraná', 'name_pt': 'Paraná'},
            {'code': 'PE', 'name': 'Pernambuco', 'name_pt': 'Pernambuco'},
            {'code': 'PI', 'name': 'Piauí', 'name_pt': 'Piauí'},
            {'code': 'RJ', 'name': 'Rio de Janeiro', 'name_pt': 'Rio de Janeiro'},
            {'code': 'RN', 'name': 'Rio Grande do Norte', 'name_pt': 'Rio Grande do Norte'},
            {'code': 'RS', 'name': 'Rio Grande do Sul', 'name_pt': 'Rio Grande do Sul'},
            {'code': 'RO', 'name': 'Rondônia', 'name_pt': 'Rondônia'},
            {'code': 'RR', 'name': 'Roraima', 'name_pt': 'Roraima'},
            {'code': 'SC', 'name': 'Santa Catarina', 'name_pt': 'Santa Catarina'},
            {'code': 'SP', 'name': 'São Paulo', 'name_pt': 'São Paulo'},
            {'code': 'SE', 'name': 'Sergipe', 'name_pt': 'Sergipe'},
            {'code': 'TO', 'name': 'Tocantins', 'name_pt': 'Tocantins'},
        ]
        
        # Estados Unidos - Todos los estados
        usa = Country.objects.get(code='USA')
        usa_states = [
            {'code': 'AL', 'name': 'Alabama', 'name_en': 'Alabama'},
            {'code': 'AK', 'name': 'Alaska', 'name_en': 'Alaska'},
            {'code': 'AZ', 'name': 'Arizona', 'name_en': 'Arizona'},
            {'code': 'AR', 'name': 'Arkansas', 'name_en': 'Arkansas'},
            {'code': 'CA', 'name': 'California', 'name_en': 'California'},
            {'code': 'CO', 'name': 'Colorado', 'name_en': 'Colorado'},
            {'code': 'CT', 'name': 'Connecticut', 'name_en': 'Connecticut'},
            {'code': 'DE', 'name': 'Delaware', 'name_en': 'Delaware'},
            {'code': 'FL', 'name': 'Florida', 'name_en': 'Florida'},
            {'code': 'GA', 'name': 'Georgia', 'name_en': 'Georgia'},
            {'code': 'HI', 'name': 'Hawaii', 'name_en': 'Hawaii'},
            {'code': 'ID', 'name': 'Idaho', 'name_en': 'Idaho'},
            {'code': 'IL', 'name': 'Illinois', 'name_en': 'Illinois'},
            {'code': 'IN', 'name': 'Indiana', 'name_en': 'Indiana'},
            {'code': 'IA', 'name': 'Iowa', 'name_en': 'Iowa'},
            {'code': 'KS', 'name': 'Kansas', 'name_en': 'Kansas'},
            {'code': 'KY', 'name': 'Kentucky', 'name_en': 'Kentucky'},
            {'code': 'LA', 'name': 'Louisiana', 'name_en': 'Louisiana'},
            {'code': 'ME', 'name': 'Maine', 'name_en': 'Maine'},
            {'code': 'MD', 'name': 'Maryland', 'name_en': 'Maryland'},
            {'code': 'MA', 'name': 'Massachusetts', 'name_en': 'Massachusetts'},
            {'code': 'MI', 'name': 'Michigan', 'name_en': 'Michigan'},
            {'code': 'MN', 'name': 'Minnesota', 'name_en': 'Minnesota'},
            {'code': 'MS', 'name': 'Mississippi', 'name_en': 'Mississippi'},
            {'code': 'MO', 'name': 'Missouri', 'name_en': 'Missouri'},
            {'code': 'MT', 'name': 'Montana', 'name_en': 'Montana'},
            {'code': 'NE', 'name': 'Nebraska', 'name_en': 'Nebraska'},
            {'code': 'NV', 'name': 'Nevada', 'name_en': 'Nevada'},
            {'code': 'NH', 'name': 'New Hampshire', 'name_en': 'New Hampshire'},
            {'code': 'NJ', 'name': 'New Jersey', 'name_en': 'New Jersey'},
            {'code': 'NM', 'name': 'New Mexico', 'name_en': 'New Mexico'},
            {'code': 'NY', 'name': 'New York', 'name_en': 'New York'},
            {'code': 'NC', 'name': 'North Carolina', 'name_en': 'North Carolina'},
            {'code': 'ND', 'name': 'North Dakota', 'name_en': 'North Dakota'},
            {'code': 'OH', 'name': 'Ohio', 'name_en': 'Ohio'},
            {'code': 'OK', 'name': 'Oklahoma', 'name_en': 'Oklahoma'},
            {'code': 'OR', 'name': 'Oregon', 'name_en': 'Oregon'},
            {'code': 'PA', 'name': 'Pennsylvania', 'name_en': 'Pennsylvania'},
            {'code': 'RI', 'name': 'Rhode Island', 'name_en': 'Rhode Island'},
            {'code': 'SC', 'name': 'South Carolina', 'name_en': 'South Carolina'},
            {'code': 'SD', 'name': 'South Dakota', 'name_en': 'South Dakota'},
            {'code': 'TN', 'name': 'Tennessee', 'name_en': 'Tennessee'},
            {'code': 'TX', 'name': 'Texas', 'name_en': 'Texas'},
            {'code': 'UT', 'name': 'Utah', 'name_en': 'Utah'},
            {'code': 'VT', 'name': 'Vermont', 'name_en': 'Vermont'},
            {'code': 'VA', 'name': 'Virginia', 'name_en': 'Virginia'},
            {'code': 'WA', 'name': 'Washington', 'name_en': 'Washington'},
            {'code': 'WV', 'name': 'West Virginia', 'name_en': 'West Virginia'},
            {'code': 'WI', 'name': 'Wisconsin', 'name_en': 'Wisconsin'},
            {'code': 'WY', 'name': 'Wyoming', 'name_en': 'Wyoming'},
            {'code': 'DC', 'name': 'District of Columbia', 'name_en': 'District of Columbia'},
        ]
        
        # España - Todas las comunidades autónomas
        spain = Country.objects.get(code='ESP')
        spain_states = [
            {'code': 'AN', 'name': 'Andalucía', 'name_es': 'Andalucía'},
            {'code': 'AR', 'name': 'Aragón', 'name_es': 'Aragón'},
            {'code': 'AS', 'name': 'Asturias', 'name_es': 'Asturias'},
            {'code': 'IB', 'name': 'Baleares', 'name_es': 'Baleares'},
            {'code': 'CN', 'name': 'Canarias', 'name_es': 'Canarias'},
            {'code': 'CB', 'name': 'Cantabria', 'name_es': 'Cantabria'},
            {'code': 'CL', 'name': 'Castilla y León', 'name_es': 'Castilla y León'},
            {'code': 'CM', 'name': 'Castilla-La Mancha', 'name_es': 'Castilla-La Mancha'},
            {'code': 'CT', 'name': 'Cataluña', 'name_es': 'Cataluña'},
            {'code': 'CE', 'name': 'Ceuta', 'name_es': 'Ceuta'},
            {'code': 'EX', 'name': 'Extremadura', 'name_es': 'Extremadura'},
            {'code': 'GA', 'name': 'Galicia', 'name_es': 'Galicia'},
            {'code': 'MD', 'name': 'Madrid', 'name_es': 'Madrid'},
            {'code': 'ML', 'name': 'Melilla', 'name_es': 'Melilla'},
            {'code': 'MC', 'name': 'Murcia', 'name_es': 'Murcia'},
            {'code': 'NC', 'name': 'Navarra', 'name_es': 'Navarra'},
            {'code': 'PV', 'name': 'País Vasco', 'name_es': 'País Vasco'},
            {'code': 'RI', 'name': 'La Rioja', 'name_es': 'La Rioja'},
            {'code': 'VC', 'name': 'Valencia', 'name_es': 'Valencia'},
        ]
        
        # Crear estados para cada país
        countries_states = [
            (argentina, argentina_states),
            (chile, chile_states),
            (uruguay, uruguay_states),
            (paraguay, paraguay_states),
            (brazil, brazil_states),
            (usa, usa_states),
            (spain, spain_states),
        ]
        
        total_created = 0
        for country, states_data in countries_states:
            country_created = 0
            for state_data in states_data:
                state, created = State.objects.get_or_create(
                    country=country,
                    code=state_data['code'],
                    defaults=state_data
                )
                if created:
                    country_created += 1
                    total_created += 1
            
            self.stdout.write(f'  ✅ {country.name}: {country_created} states created')
        
        self.stdout.write(f'  📊 Total: {total_created} states created') 