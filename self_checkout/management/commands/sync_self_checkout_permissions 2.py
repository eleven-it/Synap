"""
Sincroniza permisos Self-Checkout a permiso_sistema de AdministraNET MySQL.
Uso: python manage.py sync_self_checkout_permissions [--base-empresa X] [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import MySQLdb
import logging

from self_checkout.permissions import SCO_KIOSK, SCO_SUPERVISOR, SCO_ADMIN

logger = logging.getLogger(__name__)

SCO_PERMISSIONS_DATA = [
    {'key': SCO_KIOSK, 'nombre': 'Operar kiosco autoservicio', 'grupo': 'SELF_CHECKOUT'},
    {'key': SCO_SUPERVISOR, 'nombre': 'Supervisar kioscos', 'grupo': 'SELF_CHECKOUT'},
    {'key': SCO_ADMIN, 'nombre': 'Administrar módulo Self-Checkout', 'grupo': 'SELF_CHECKOUT'},
]


class Command(BaseCommand):
    help = 'Sincroniza permisos Self-Checkout a permiso_sistema (MySQL)'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, help='Base de datos de la empresa')
        parser.add_argument('--dry-run', action='store_true', help='Solo mostrar, no escribir')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no se escribirán cambios'))

        mysql_config = settings.DATABASES['mysql']
        try:
            conn = MySQLdb.connect(
                host=mysql_config['HOST'],
                port=int(mysql_config.get('PORT', 3306)),
                user=mysql_config['USER'],
                passwd=mysql_config['PASSWORD'],
                db=base,
                charset='latin1',
            )
            cursor = conn.cursor()

            for p in SCO_PERMISSIONS_DATA:
                cursor.execute("SELECT id_permiso_sistema FROM permiso_sistema WHERE key_permiso = %s", [p['key']])
                if cursor.fetchone():
                    self.stdout.write(f'  Ya existe: {p["key"]}')
                else:
                    if not dry_run:
                        try:
                            cursor.execute("""
                                INSERT INTO permiso_sistema
                                (key_permiso, nombre_permiso, detalle_permiso, grupo_permiso, tipo_permiso, default_permiso, detalle_valor_permiso)
                                VALUES (%s, %s, %s, %s, 'Si-No', 'No', 'Si-No')
                            """, [p['key'], p['nombre'], p['nombre'], p['grupo']])
                        except MySQLdb.Error as e:
                            if 'Column' in str(e):
                                cursor.execute(
                                    "INSERT INTO permiso_sistema (key_permiso) VALUES (%s)",
                                    [p['key']]
                                )
                            else:
                                raise
                    self.stdout.write(self.style.SUCCESS(f'  Creado: {p["key"]}'))

            if not dry_run:
                conn.commit()

            cursor.close()
            conn.close()
            self.stdout.write(self.style.SUCCESS(f'Permisos Self-Checkout sincronizados en {base}'))
        except MySQLdb.Error as e:
            self.stderr.write(self.style.ERROR(f'Error MySQL: {e}'))
