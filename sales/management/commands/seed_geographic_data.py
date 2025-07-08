from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from sales.models import Country, State, Language


class Command(BaseCommand):
    help = 'Poblar datos geográficos y de idiomas'

    def handle(self, *args, **options):
        self.stdout.write('Poblando datos geográficos...')
        
        # Crear idiomas
        self.seed_languages()
        
        # Crear países
        self.seed_countries()
        
        # Crear provincias/estados
        self.seed_states()
        
        self.stdout.write(
            self.style.SUCCESS('Datos geográficos poblados exitosamente')
        )

    def seed_languages(self):
        """Poblar idiomas soportados"""
        languages_data = [
            {
                'code': 'es',
                'name': 'Spanish',
                'name_native': 'Español',
                'is_default': True
            },
            {
                'code': 'en',
                'name': 'English',
                'name_native': 'English',
                'is_default': False
            },
            {
                'code': 'pt',
                'name': 'Portuguese',
                'name_native': 'Português',
                'is_default': False
            },
            {
                'code': 'fr',
                'name': 'French',
                'name_native': 'Français',
                'is_default': False
            },
            {
                'code': 'it',
                'name': 'Italian',
                'name_native': 'Italiano',
                'is_default': False
            },
        ]
        
        for lang_data in languages_data:
            Language.objects.get_or_create(
                code=lang_data['code'],
                defaults=lang_data
            )
        
        self.stdout.write(f'  - {len(languages_data)} idiomas creados')

    def seed_countries(self):
        """Poblar países de habla hispana, Brasil, México, Estados Unidos y España"""
        countries_data = [
            # Argentina
            {
                'code': 'ARG',
                'name': 'Argentina',
                'name_es': 'Argentina',
                'name_en': 'Argentina',
                'name_pt': 'Argentina',
                'phone_code': '+54',
                'currency_code': 'ARS',
                'timezone': 'America/Argentina/Buenos_Aires'
            },
            # Brasil
            {
                'code': 'BRA',
                'name': 'Brazil',
                'name_es': 'Brasil',
                'name_en': 'Brazil',
                'name_pt': 'Brasil',
                'phone_code': '+55',
                'currency_code': 'BRL',
                'timezone': 'America/Sao_Paulo'
            },
            # Chile
            {
                'code': 'CHL',
                'name': 'Chile',
                'name_es': 'Chile',
                'name_en': 'Chile',
                'name_pt': 'Chile',
                'phone_code': '+56',
                'currency_code': 'CLP',
                'timezone': 'America/Santiago'
            },
            # Colombia
            {
                'code': 'COL',
                'name': 'Colombia',
                'name_es': 'Colombia',
                'name_en': 'Colombia',
                'name_pt': 'Colômbia',
                'phone_code': '+57',
                'currency_code': 'COP',
                'timezone': 'America/Bogota'
            },
            # Costa Rica
            {
                'code': 'CRI',
                'name': 'Costa Rica',
                'name_es': 'Costa Rica',
                'name_en': 'Costa Rica',
                'name_pt': 'Costa Rica',
                'phone_code': '+506',
                'currency_code': 'CRC',
                'timezone': 'America/Costa_Rica'
            },
            # Ecuador
            {
                'code': 'ECU',
                'name': 'Ecuador',
                'name_es': 'Ecuador',
                'name_en': 'Ecuador',
                'name_pt': 'Equador',
                'phone_code': '+593',
                'currency_code': 'USD',
                'timezone': 'America/Guayaquil'
            },
            # El Salvador
            {
                'code': 'SLV',
                'name': 'El Salvador',
                'name_es': 'El Salvador',
                'name_en': 'El Salvador',
                'name_pt': 'El Salvador',
                'phone_code': '+503',
                'currency_code': 'USD',
                'timezone': 'America/El_Salvador'
            },
            # España
            {
                'code': 'ESP',
                'name': 'Spain',
                'name_es': 'España',
                'name_en': 'Spain',
                'name_pt': 'Espanha',
                'phone_code': '+34',
                'currency_code': 'EUR',
                'timezone': 'Europe/Madrid'
            },
            # Estados Unidos
            {
                'code': 'USA',
                'name': 'United States',
                'name_es': 'Estados Unidos',
                'name_en': 'United States',
                'name_pt': 'Estados Unidos',
                'phone_code': '+1',
                'currency_code': 'USD',
                'timezone': 'America/New_York'
            },
            # Guatemala
            {
                'code': 'GTM',
                'name': 'Guatemala',
                'name_es': 'Guatemala',
                'name_en': 'Guatemala',
                'name_pt': 'Guatemala',
                'phone_code': '+502',
                'currency_code': 'GTQ',
                'timezone': 'America/Guatemala'
            },
            # Honduras
            {
                'code': 'HND',
                'name': 'Honduras',
                'name_es': 'Honduras',
                'name_en': 'Honduras',
                'name_pt': 'Honduras',
                'phone_code': '+504',
                'currency_code': 'HNL',
                'timezone': 'America/Tegucigalpa'
            },
            # México
            {
                'code': 'MEX',
                'name': 'Mexico',
                'name_es': 'México',
                'name_en': 'Mexico',
                'name_pt': 'México',
                'phone_code': '+52',
                'currency_code': 'MXN',
                'timezone': 'America/Mexico_City'
            },
            # Nicaragua
            {
                'code': 'NIC',
                'name': 'Nicaragua',
                'name_es': 'Nicaragua',
                'name_en': 'Nicaragua',
                'name_pt': 'Nicarágua',
                'phone_code': '+505',
                'currency_code': 'NIO',
                'timezone': 'America/Managua'
            },
            # Panamá
            {
                'code': 'PAN',
                'name': 'Panama',
                'name_es': 'Panamá',
                'name_en': 'Panama',
                'name_pt': 'Panamá',
                'phone_code': '+507',
                'currency_code': 'USD',
                'timezone': 'America/Panama'
            },
            # Paraguay
            {
                'code': 'PRY',
                'name': 'Paraguay',
                'name_es': 'Paraguay',
                'name_en': 'Paraguay',
                'name_pt': 'Paraguai',
                'phone_code': '+595',
                'currency_code': 'PYG',
                'timezone': 'America/Asuncion'
            },
            # Perú
            {
                'code': 'PER',
                'name': 'Peru',
                'name_es': 'Perú',
                'name_en': 'Peru',
                'name_pt': 'Peru',
                'phone_code': '+51',
                'currency_code': 'PEN',
                'timezone': 'America/Lima'
            },
            # República Dominicana
            {
                'code': 'DOM',
                'name': 'Dominican Republic',
                'name_es': 'República Dominicana',
                'name_en': 'Dominican Republic',
                'name_pt': 'República Dominicana',
                'phone_code': '+1',
                'currency_code': 'DOP',
                'timezone': 'America/Santo_Domingo'
            },
            # Uruguay
            {
                'code': 'URY',
                'name': 'Uruguay',
                'name_es': 'Uruguay',
                'name_en': 'Uruguay',
                'name_pt': 'Uruguai',
                'phone_code': '+598',
                'currency_code': 'UYU',
                'timezone': 'America/Montevideo'
            },
            # Venezuela
            {
                'code': 'VEN',
                'name': 'Venezuela',
                'name_es': 'Venezuela',
                'name_en': 'Venezuela',
                'name_pt': 'Venezuela',
                'phone_code': '+58',
                'currency_code': 'VES',
                'timezone': 'America/Caracas'
            },
        ]
        
        for country_data in countries_data:
            Country.objects.get_or_create(
                code=country_data['code'],
                defaults=country_data
            )
        
        self.stdout.write(f'  - {len(countries_data)} países creados')

    def seed_states(self):
        """Poblar provincias/estados para los países principales"""
        
        # Argentina - Provincias
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
        
        for state_data in argentina_states:
            State.objects.get_or_create(
                country=argentina,
                code=state_data['code'],
                defaults=state_data
            )
        
        # Brasil - Estados principales
        brazil = Country.objects.get(code='BRA')
        brazil_states = [
            {'code': 'SP', 'name': 'São Paulo', 'name_pt': 'São Paulo'},
            {'code': 'RJ', 'name': 'Rio de Janeiro', 'name_pt': 'Rio de Janeiro'},
            {'code': 'MG', 'name': 'Minas Gerais', 'name_pt': 'Minas Gerais'},
            {'code': 'RS', 'name': 'Rio Grande do Sul', 'name_pt': 'Rio Grande do Sul'},
            {'code': 'PR', 'name': 'Paraná', 'name_pt': 'Paraná'},
            {'code': 'SC', 'name': 'Santa Catarina', 'name_pt': 'Santa Catarina'},
            {'code': 'BA', 'name': 'Bahia', 'name_pt': 'Bahia'},
            {'code': 'GO', 'name': 'Goiás', 'name_pt': 'Goiás'},
            {'code': 'PE', 'name': 'Pernambuco', 'name_pt': 'Pernambuco'},
            {'code': 'CE', 'name': 'Ceará', 'name_pt': 'Ceará'},
        ]
        
        for state_data in brazil_states:
            State.objects.get_or_create(
                country=brazil,
                code=state_data['code'],
                defaults=state_data
            )
        
        # México - Estados principales
        mexico = Country.objects.get(code='MEX')
        mexico_states = [
            {'code': 'CDMX', 'name': 'Ciudad de México', 'name_es': 'Ciudad de México'},
            {'code': 'JAL', 'name': 'Jalisco', 'name_es': 'Jalisco'},
            {'code': 'NLE', 'name': 'Nuevo León', 'name_es': 'Nuevo León'},
            {'code': 'BCN', 'name': 'Baja California', 'name_es': 'Baja California'},
            {'code': 'SON', 'name': 'Sonora', 'name_es': 'Sonora'},
            {'code': 'CHH', 'name': 'Chihuahua', 'name_es': 'Chihuahua'},
            {'code': 'COA', 'name': 'Coahuila', 'name_es': 'Coahuila'},
            {'code': 'TAM', 'name': 'Tamaulipas', 'name_es': 'Tamaulipas'},
            {'code': 'VER', 'name': 'Veracruz', 'name_es': 'Veracruz'},
            {'code': 'PUE', 'name': 'Puebla', 'name_es': 'Puebla'},
        ]
        
        for state_data in mexico_states:
            State.objects.get_or_create(
                country=mexico,
                code=state_data['code'],
                defaults=state_data
            )
        
        # España - Comunidades Autónomas principales
        spain = Country.objects.get(code='ESP')
        spain_states = [
            {'code': 'MAD', 'name': 'Madrid', 'name_es': 'Madrid'},
            {'code': 'CAT', 'name': 'Cataluña', 'name_es': 'Cataluña'},
            {'code': 'AND', 'name': 'Andalucía', 'name_es': 'Andalucía'},
            {'code': 'VAL', 'name': 'Comunidad Valenciana', 'name_es': 'Comunidad Valenciana'},
            {'code': 'GAL', 'name': 'Galicia', 'name_es': 'Galicia'},
            {'code': 'PVA', 'name': 'País Vasco', 'name_es': 'País Vasco'},
            {'code': 'CAN', 'name': 'Canarias', 'name_es': 'Canarias'},
            {'code': 'CYL', 'name': 'Castilla y León', 'name_es': 'Castilla y León'},
            {'code': 'CLM', 'name': 'Castilla-La Mancha', 'name_es': 'Castilla-La Mancha'},
            {'code': 'AST', 'name': 'Asturias', 'name_es': 'Asturias'},
        ]
        
        for state_data in spain_states:
            State.objects.get_or_create(
                country=spain,
                code=state_data['code'],
                defaults=state_data
            )
        
        # Estados Unidos - Estados principales
        usa = Country.objects.get(code='USA')
        usa_states = [
            {'code': 'CA', 'name': 'California', 'name_en': 'California'},
            {'code': 'TX', 'name': 'Texas', 'name_en': 'Texas'},
            {'code': 'FL', 'name': 'Florida', 'name_en': 'Florida'},
            {'code': 'NY', 'name': 'New York', 'name_en': 'New York'},
            {'code': 'IL', 'name': 'Illinois', 'name_en': 'Illinois'},
            {'code': 'PA', 'name': 'Pennsylvania', 'name_en': 'Pennsylvania'},
            {'code': 'OH', 'name': 'Ohio', 'name_en': 'Ohio'},
            {'code': 'GA', 'name': 'Georgia', 'name_en': 'Georgia'},
            {'code': 'NC', 'name': 'North Carolina', 'name_en': 'North Carolina'},
            {'code': 'MI', 'name': 'Michigan', 'name_en': 'Michigan'},
        ]
        
        for state_data in usa_states:
            State.objects.get_or_create(
                country=usa,
                code=state_data['code'],
                defaults=state_data
            )
        
        total_states = len(argentina_states) + len(brazil_states) + len(mexico_states) + len(spain_states) + len(usa_states)
        self.stdout.write(f'  - {total_states} estados/provincias creados') 