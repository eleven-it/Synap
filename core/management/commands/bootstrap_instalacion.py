"""
Bootstrap de primera instalación Synap (PostgreSQL vacío o sin módulos base activos).

Activa la cadena mínima core → login → dashboard → reports, permisos en Postgres
y esquema synap_* opcional en MySQL AdministraNET.
"""
import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

from core.dependency_manager import dependency_manager
from core.menu_manager import menu_manager
from core.module_manager import module_manager
from core.models import Permiso

logger = logging.getLogger(__name__)

# Cadena mínima: reports depende de dashboard → login → core
MODULOS_BOOTSTRAP = ['core', 'login', 'dashboard', 'reports']


class Command(BaseCommand):
    help = (
        'Bootstrap de primera instalación: módulos core/login/dashboard/reports, '
        'permisos Postgres y tablas synap_* opcionales en AdministraNET.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ejecutar aunque el bootstrap ya se haya aplicado',
        )
        parser.add_argument(
            '--skip-permisos-mysql',
            action='store_true',
            help='No crear tablas synap_* ni sembrar catálogo en MySQL (permiso_sistema no se toca)',
        )
        parser.add_argument(
            '--base-empresa',
            type=str,
            default='',
            help='Base MySQL empresa para apply_synap_permisos_tables (requerida si no se omite MySQL)',
        )

    def handle(self, *args, **options):
        force = options['force']
        if not force and not self._necesita_bootstrap():
            self.stdout.write(
                self.style.SUCCESS('Bootstrap ya aplicado; omitiendo (use --force para repetir).')
            )
            return

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Bootstrap de instalación Synap'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        self._paso_reports()
        self._paso_modulos()
        self._paso_permisos_postgres()
        if not options['skip_permisos_mysql']:
            self._paso_permisos_mysql(options.get('base_empresa') or None)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Bootstrap completado.'))

    def _necesita_bootstrap(self):
        """True si falta la cadena mínima de módulos activos."""
        for nombre in MODULOS_BOOTSTRAP:
            if not module_manager.is_module_active(nombre):
                return True
        return False

    @staticmethod
    def _paso_reports():
        call_command('setup_reports_installation', skip_migrations=True, verbosity=1)

    def _paso_modulos(self):
        self.stdout.write('')
        self.stdout.write('Activando módulos: ' + ', '.join(MODULOS_BOOTSTRAP))
        orden = dependency_manager.get_activation_order(MODULOS_BOOTSTRAP)
        for nombre in orden:
            if nombre not in MODULOS_BOOTSTRAP:
                continue
            ok, mensaje = module_manager.activate_module(nombre)
            if ok:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {nombre}: {mensaje}'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {nombre}: {mensaje}'))
        menu_manager.reload_module_menus()

    def _paso_permisos_postgres(self):
        self.stdout.write('')
        self.stdout.write('Sincronizando permisos y roles en PostgreSQL...')
        if not Permiso.objects.exists():
            call_command('crear_roles_base', verbosity=1)
        else:
            call_command('sincronizar_permisos', verbosity=1)
        call_command('asignar_roles_predeterminados', verbosity=1)

    def _paso_permisos_mysql(self, base_empresa):
        self.stdout.write('')
        if not base_empresa:
            self.stdout.write(
                self.style.WARNING(
                    '  ⚠ Omitiendo MySQL: indique --base-empresa para apply_synap_permisos_tables '
                    '(o use --skip-permisos-mysql).'
                )
            )
            return
        self.stdout.write(
            f'Creando tablas synap_* y sembrando catálogo en MySQL ({base_empresa})...'
        )
        try:
            call_command('apply_synap_permisos_tables', base_empresa, verbosity=1)
        except Exception as exc:
            logger.warning('Bootstrap: apply_synap_permisos_tables omitido: %s', exc)
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠ Esquema synap_* omitido (no bloquea el arranque): {exc}'
                )
            )
