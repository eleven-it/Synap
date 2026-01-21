"""
Comando de gestión para crear los permisos predeterminados de SIA
"""
from django.core.management.base import BaseCommand
from core.permissions_utils import ensure_sia_permissions_in_postgres


class Command(BaseCommand):
    help = 'Crea los permisos predeterminados para el módulo SIA en PostgreSQL'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando creación/sincronización de permisos SIA en PostgreSQL...')
        
        creados, actualizados = ensure_sia_permissions_in_postgres(verbose=True)
        
        if creados > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✓ {creados} permisos creados')
            )
        if actualizados > 0:
            self.stdout.write(
                self.style.WARNING(f'↻ {actualizados} permisos actualizados')
            )
        
        if creados == 0 and actualizados == 0:
            self.stdout.write(
                self.style.SUCCESS('Todos los permisos SIA ya existen y están actualizados.')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Proceso completado: {creados} creados, {actualizados} actualizados'
            )
        )

