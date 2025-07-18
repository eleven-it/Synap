"""
Comando para poblar las responsabilidades fiscales oficiales de todos los países
Carga las listas oficiales de tipos de contribuyentes según la legislación de cada país
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import FiscalResponsibility, Country


class Command(BaseCommand):
    help = 'Pobla las responsabilidades fiscales oficiales de todos los países'

    def add_arguments(self, parser):
        parser.add_argument(
            '--country',
            type=str,
            help='Código de país específico para poblar (ej: AR, CL, UY)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la recreación de responsabilidades existentes',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se crearía sin ejecutar',
        )

    def handle(self, *args, **options):
        country_code = options['country']
        force = options['force']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN - No se crearán registros'))

        # Definir responsabilidades fiscales por país
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

        # Filtrar por país específico si se especifica
        if country_code:
            country_code = country_code.upper()
            if country_code not in responsibilities_data:
                self.stdout.write(
                    self.style.ERROR(f'País {country_code} no encontrado en la lista de responsabilidades')
                )
                return
            responsibilities_data = {country_code: responsibilities_data[country_code]}

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for country_code, responsibilities in responsibilities_data.items():
                try:
                    country = Country.objects.get(code=country_code)
                    self.stdout.write(f'Procesando país: {country.name} ({country_code})')
                    
                    for code, name in responsibilities.items():
                        if dry_run:
                            self.stdout.write(f'  - Crearía: {code} - {name}')
                            continue
                        
                        # Crear o actualizar responsabilidad fiscal
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
                            created_count += 1
                            self.stdout.write(f'  ✓ Creado: {code} - {name}')
                        else:
                            if force:
                                responsibility.name = name
                                responsibility.description = f'Responsabilidad fiscal oficial de {country.name}'
                                responsibility.is_active = True
                                responsibility.save()
                                updated_count += 1
                                self.stdout.write(f'  ↻ Actualizado: {code} - {name}')
                            else:
                                self.stdout.write(f'  - Existe: {code} - {name}')
                                
                except Country.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'País {country_code} no encontrado en la base de datos')
                    )
                    continue

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Proceso completado. Creados: {created_count}, Actualizados: {updated_count}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Dry-run completado. Revisa los registros que se crearían.')
            ) 