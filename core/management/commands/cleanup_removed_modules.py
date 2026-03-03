"""
Elimina de ModuleConfig los módulos que ya no existen en el código:
administraNET_integration, accounting, finance, inventory, purchases,
logistics, reports_ai, tiendanube, sia.
"""

from django.core.management.base import BaseCommand

MODULOS_ELIMINADOS = [
    'administraNET_integration',
    'accounting',
    'finance',
    'inventory',
    'purchases',
    'logistics',
    'reports_ai',
    'tiendanube',
    'sia',
]


class Command(BaseCommand):
    help = "Elimina registros de ModuleConfig para módulos que ya no están en el sistema."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar cuántos registros se eliminarían sin ejecutar',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        try:
            from core.models import ModuleConfig

            total = 0
            for name in MODULOS_ELIMINADOS:
                qs = ModuleConfig.objects.filter(name=name)
                count = qs.count()
                if count:
                    total += count
                    if dry_run:
                        self.stdout.write(f'  Se eliminarían {count} registro(s) de "{name}"')
                    else:
                        qs.delete()
                        self.stdout.write(self.style.SUCCESS(f'  Eliminados {count} registro(s) de "{name}"'))

            if total == 0:
                self.stdout.write(self.style.SUCCESS('No hay registros de módulos eliminados en ModuleConfig.'))
            elif dry_run:
                self.stdout.write(
                    self.style.WARNING(f'\nTotal: se eliminarían {total} registro(s). Ejecute sin --dry-run para aplicar.')
                )
            else:
                self.stdout.write(self.style.SUCCESS(f'\nTotal eliminados: {total} registro(s).'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
