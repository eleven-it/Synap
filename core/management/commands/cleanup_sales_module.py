"""
Comando para limpiar el registro del módulo Sales en la base de datos.
El módulo Sales no existe como app Django; este comando elimina ModuleConfig
con name='sales' para que no aparezca en la gestión de módulos ni en el menú.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Elimina el registro del módulo 'sales' de ModuleConfig (módulo no presente en el código)."

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

            qs = ModuleConfig.objects.filter(name='sales')
            count = qs.count()

            if count == 0:
                self.stdout.write(
                    self.style.SUCCESS('No hay registros del módulo "sales" en ModuleConfig.')
                )
                return

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'Se eliminarían {count} registro(s) del módulo "sales". Ejecute sin --dry-run para aplicar.')
                )
                return

            qs.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Se eliminaron {count} registro(s) del módulo "sales" en ModuleConfig.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
