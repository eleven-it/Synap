"""
Comando para limpiar el cache de permisos de un usuario específico
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Limpia el cache de permisos para un usuario específico o todos los usuarios'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Limpiar todo el cache de permisos',
        )

    def handle(self, *args, **options):
        if options['all']:
            cache.clear()
            self.stdout.write(
                self.style.SUCCESS('✅ Todo el cache ha sido limpiado')
            )
            self.stdout.write(
                '\n⚠️  IMPORTANTE: Todos los usuarios deben cerrar sesión y volver a iniciar sesión'
            )
            self.stdout.write(
                '   para que se recarguen los permisos desde MySQL.'
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Usa --all para limpiar todo el cache')
            )
            self.stdout.write(
                '\nAlternativamente, los usuarios pueden cerrar sesión y volver a iniciar sesión'
            )
            self.stdout.write(
                'para que se recarguen automáticamente sus permisos.'
            )













