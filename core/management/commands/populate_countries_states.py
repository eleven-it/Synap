from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from core.models import Country, State


class Command(BaseCommand):
    help = 'Populate countries and states with initial data'

    def handle(self, *args, **options):
        self.stdout.write('Populating countries and states...')
        
        # Crear países principales
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
                'states': [
                    {'name': 'Buenos Aires', 'code': 'BA'},
                    {'name': 'Córdoba', 'code': 'CB'},
                    {'name': 'Santa Fe', 'code': 'SF'},
                    {'name': 'Mendoza', 'code': 'MZ'},
                    {'name': 'Tucumán', 'code': 'TM'},
                    {'name': 'Entre Ríos', 'code': 'ER'},
                    {'name': 'Salta', 'code': 'SA'},
                    {'name': 'Misiones', 'code': 'MI'},
                    {'name': 'Chaco', 'code': 'CC'},
                    {'name': 'Corrientes', 'code': 'CT'},
                    {'name': 'Santiago del Estero', 'code': 'SE'},
                    {'name': 'San Juan', 'code': 'SJ'},
                    {'name': 'Jujuy', 'code': 'JY'},
                    {'name': 'Río Negro', 'code': 'RN'},
                    {'name': 'Neuquén', 'code': 'NQ'},
                    {'name': 'Formosa', 'code': 'FM'},
                    {'name': 'Chubut', 'code': 'CH'},
                    {'name': 'San Luis', 'code': 'SL'},
                    {'name': 'Catamarca', 'code': 'CA'},
                    {'name': 'La Rioja', 'code': 'LR'},
                    {'name': 'La Pampa', 'code': 'LP'},
                    {'name': 'Tierra del Fuego', 'code': 'TF'},
                ]
            },
            {
                'name': 'México',
                'name_es': 'México',
                'name_en': 'Mexico',
                'name_pt': 'México',
                'code': 'MEX',
                'code_2': 'MX',
                'phone_code': '+52',
                'currency_code': 'MXN',
                'timezone': 'America/Mexico_City',
                'states': [
                    {'name': 'Jalisco', 'code': 'JAL'},
                    {'name': 'Nuevo León', 'code': 'NL'},
                    {'name': 'Baja California', 'code': 'BC'},
                    {'name': 'Baja California Sur', 'code': 'BCS'},
                    {'name': 'Sonora', 'code': 'SON'},
                    {'name': 'Chihuahua', 'code': 'CHH'},
                    {'name': 'Coahuila', 'code': 'COA'},
                    {'name': 'Tamaulipas', 'code': 'TAM'},
                    {'name': 'Sinaloa', 'code': 'SIN'},
                    {'name': 'Durango', 'code': 'DUR'},
                    {'name': 'Zacatecas', 'code': 'ZAC'},
                    {'name': 'San Luis Potosí', 'code': 'SLP'},
                    {'name': 'Aguascalientes', 'code': 'AGS'},
                    {'name': 'Guanajuato', 'code': 'GTO'},
                    {'name': 'Querétaro', 'code': 'QRO'},
                    {'name': 'Hidalgo', 'code': 'HGO'},
                    {'name': 'México', 'code': 'MEX'},
                    {'name': 'Morelos', 'code': 'MOR'},
                    {'name': 'Puebla', 'code': 'PUE'},
                    {'name': 'Tlaxcala', 'code': 'TLA'},
                    {'name': 'Veracruz', 'code': 'VER'},
                    {'name': 'Tabasco', 'code': 'TAB'},
                    {'name': 'Campeche', 'code': 'CAM'},
                    {'name': 'Yucatán', 'code': 'YUC'},
                    {'name': 'Quintana Roo', 'code': 'ROO'},
                    {'name': 'Chiapas', 'code': 'CHP'},
                    {'name': 'Oaxaca', 'code': 'OAX'},
                    {'name': 'Guerrero', 'code': 'GRO'},
                    {'name': 'Michoacán', 'code': 'MIC'},
                    {'name': 'Colima', 'code': 'COL'},
                    {'name': 'Nayarit', 'code': 'NAY'},
                    {'name': 'Distrito Federal', 'code': 'DF'},
                ]
            },
            {
                'name': 'Brasil',
                'name_es': 'Brasil',
                'name_en': 'Brazil',
                'name_pt': 'Brasil',
                'code': 'BRA',
                'code_2': 'BR',
                'phone_code': '+55',
                'currency_code': 'BRL',
                'timezone': 'America/Sao_Paulo',
                'states': [
                    {'name': 'São Paulo', 'code': 'SP'},
                    {'name': 'Minas Gerais', 'code': 'MG'},
                    {'name': 'Rio de Janeiro', 'code': 'RJ'},
                    {'name': 'Bahia', 'code': 'BA'},
                    {'name': 'Rio Grande do Sul', 'code': 'RS'},
                    {'name': 'Paraná', 'code': 'PR'},
                    {'name': 'Pernambuco', 'code': 'PE'},
                    {'name': 'Ceará', 'code': 'CE'},
                    {'name': 'Pará', 'code': 'PA'},
                    {'name': 'Maranhão', 'code': 'MA'},
                    {'name': 'Santa Catarina', 'code': 'SC'},
                    {'name': 'Goiás', 'code': 'GO'},
                    {'name': 'Paraíba', 'code': 'PB'},
                    {'name': 'Espírito Santo', 'code': 'ES'},
                    {'name': 'Amazonas', 'code': 'AM'},
                    {'name': 'Rio Grande do Norte', 'code': 'RN'},
                    {'name': 'Alagoas', 'code': 'AL'},
                    {'name': 'Piauí', 'code': 'PI'},
                    {'name': 'Mato Grosso', 'code': 'MT'},
                    {'name': 'Mato Grosso do Sul', 'code': 'MS'},
                    {'name': 'Sergipe', 'code': 'SE'},
                    {'name': 'Rondônia', 'code': 'RO'},
                    {'name': 'Tocantins', 'code': 'TO'},
                    {'name': 'Acre', 'code': 'AC'},
                    {'name': 'Amapá', 'code': 'AP'},
                    {'name': 'Roraima', 'code': 'RR'},
                    {'name': 'Distrito Federal', 'code': 'DF'},
                ]
            },
            {
                'name': 'Estados Unidos',
                'name_es': 'Estados Unidos',
                'name_en': 'United States',
                'name_pt': 'Estados Unidos',
                'code': 'USA',
                'code_2': 'US',
                'phone_code': '+1',
                'currency_code': 'USD',
                'timezone': 'America/New_York',
                'states': [
                    {'name': 'California', 'code': 'CA'},
                    {'name': 'Texas', 'code': 'TX'},
                    {'name': 'Florida', 'code': 'FL'},
                    {'name': 'New York', 'code': 'NY'},
                    {'name': 'Illinois', 'code': 'IL'},
                    {'name': 'Pennsylvania', 'code': 'PA'},
                    {'name': 'Ohio', 'code': 'OH'},
                    {'name': 'Georgia', 'code': 'GA'},
                    {'name': 'North Carolina', 'code': 'NC'},
                    {'name': 'Michigan', 'code': 'MI'},
                    {'name': 'New Jersey', 'code': 'NJ'},
                    {'name': 'Virginia', 'code': 'VA'},
                    {'name': 'Washington', 'code': 'WA'},
                    {'name': 'Arizona', 'code': 'AZ'},
                    {'name': 'Massachusetts', 'code': 'MA'},
                    {'name': 'Tennessee', 'code': 'TN'},
                    {'name': 'Indiana', 'code': 'IN'},
                    {'name': 'Missouri', 'code': 'MO'},
                    {'name': 'Maryland', 'code': 'MD'},
                    {'name': 'Colorado', 'code': 'CO'},
                    {'name': 'Wisconsin', 'code': 'WI'},
                    {'name': 'Minnesota', 'code': 'MN'},
                    {'name': 'South Carolina', 'code': 'SC'},
                    {'name': 'Alabama', 'code': 'AL'},
                    {'name': 'Louisiana', 'code': 'LA'},
                    {'name': 'Kentucky', 'code': 'KY'},
                    {'name': 'Oregon', 'code': 'OR'},
                    {'name': 'Oklahoma', 'code': 'OK'},
                    {'name': 'Connecticut', 'code': 'CT'},
                    {'name': 'Utah', 'code': 'UT'},
                    {'name': 'Iowa', 'code': 'IA'},
                    {'name': 'Nevada', 'code': 'NV'},
                    {'name': 'Arkansas', 'code': 'AR'},
                    {'name': 'Mississippi', 'code': 'MS'},
                    {'name': 'Kansas', 'code': 'KS'},
                    {'name': 'New Mexico', 'code': 'NM'},
                    {'name': 'Nebraska', 'code': 'NE'},
                    {'name': 'West Virginia', 'code': 'WV'},
                    {'name': 'Idaho', 'code': 'ID'},
                    {'name': 'Hawaii', 'code': 'HI'},
                    {'name': 'New Hampshire', 'code': 'NH'},
                    {'name': 'Maine', 'code': 'ME'},
                    {'name': 'Montana', 'code': 'MT'},
                    {'name': 'Rhode Island', 'code': 'RI'},
                    {'name': 'Delaware', 'code': 'DE'},
                    {'name': 'South Dakota', 'code': 'SD'},
                    {'name': 'North Dakota', 'code': 'ND'},
                    {'name': 'Alaska', 'code': 'AK'},
                    {'name': 'Vermont', 'code': 'VT'},
                    {'name': 'Wyoming', 'code': 'WY'},
                ]
            },
            {
                'name': 'España',
                'name_es': 'España',
                'name_en': 'Spain',
                'name_pt': 'Espanha',
                'code': 'ESP',
                'code_2': 'ES',
                'phone_code': '+34',
                'currency_code': 'EUR',
                'timezone': 'Europe/Madrid',
                'states': [
                    {'name': 'Andalucía', 'code': 'AN'},
                    {'name': 'Cataluña', 'code': 'CT'},
                    {'name': 'Madrid', 'code': 'MD'},
                    {'name': 'Valencia', 'code': 'VC'},
                    {'name': 'Galicia', 'code': 'GA'},
                    {'name': 'Castilla y León', 'code': 'CL'},
                    {'name': 'País Vasco', 'code': 'PV'},
                    {'name': 'Castilla-La Mancha', 'code': 'CM'},
                    {'name': 'Canarias', 'code': 'CN'},
                    {'name': 'Murcia', 'code': 'MC'},
                    {'name': 'Aragón', 'code': 'AR'},
                    {'name': 'Extremadura', 'code': 'EX'},
                    {'name': 'Baleares', 'code': 'IB'},
                    {'name': 'Asturias', 'code': 'AS'},
                    {'name': 'Navarra', 'code': 'NC'},
                    {'name': 'Cantabria', 'code': 'CB'},
                    {'name': 'La Rioja', 'code': 'RI'},
                    {'name': 'Ceuta', 'code': 'CE'},
                    {'name': 'Melilla', 'code': 'ML'},
                ]
            },
        ]
        
        created_countries = 0
        created_states = 0
        
        for country_data in countries_data:
            states_data = country_data.pop('states')
            
            country, created = Country.objects.get_or_create(
                code=country_data['code'],
                defaults=country_data
            )
            
            if created:
                created_countries += 1
                self.stdout.write(f'Created country: {country.name}')
            
            for state_data in states_data:
                state, created = State.objects.get_or_create(
                    country=country,
                    name=state_data['name'],
                    defaults=state_data
                )
                
                if created:
                    created_states += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated {created_countries} countries and {created_states} states'
            )
        ) 