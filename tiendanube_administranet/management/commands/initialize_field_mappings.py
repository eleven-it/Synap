"""
Comando de gestión para inicializar los mapeos de campos por defecto.
"""

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from tiendanube_administranet.services.dynamic_mapping_service import FieldMappingInitializer


class Command(BaseCommand):
    help = 'Inicializa los mapeos de campos por defecto entre Tiendanube y AdministraNET'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mapping-type',
            type=str,
            choices=['customer', 'product', 'order', 'variant', 'category', 'all'],
            default='all',
            help='Tipo de mapeo a inicializar (default: all)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la recreación de mapeos existentes'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin ejecutar cambios'
        )

    def handle(self, *args, **options):
        mapping_type = options['mapping_type']
        force = options['force']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(
                f'Inicializando mapeos de campos para: {mapping_type}'
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY-RUN: No se realizarán cambios')
            )

        try:
            if mapping_type == 'all':
                if not dry_run:
                    FieldMappingInitializer.initialize_all_mappings()
                self.stdout.write(
                    self.style.SUCCESS('✓ Todos los mapeos inicializados correctamente')
                )
            elif mapping_type == 'customer':
                if not dry_run:
                    FieldMappingInitializer.initialize_customer_mappings()
                self.stdout.write(
                    self.style.SUCCESS('✓ Mapeos de clientes inicializados correctamente')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Mapeos para {mapping_type} aún no implementados')
                )

            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        '✅ Inicialización completada. Puedes ver los mapeos en: '
                        '/tiendanube-adminet/mappings/'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ Simulación completada')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error durante la inicialización: {str(e)}')
            )
            raise 