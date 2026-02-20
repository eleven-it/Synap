"""
Aplica migración 004: columnas ultimo_error_confirmacion, ultimo_intento_confirmacion en self_checkout_cart.
Uso: python manage.py self_checkout_apply_migration_004 --base-empresa <NOMBRE>
"""
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Aplica migración 004: columnas para error_confirmacion en self_checkout_cart'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, default=None,
                            help='Nombre de la base de datos de la empresa')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        self.stdout.write(f'Aplicando migración 004 en base: {base}')

        try:
            import MySQLdb
        except ImportError:
            self.stderr.write(self.style.ERROR('Instalar: pip install mysqlclient'))
            return

        mysql_config = settings.DATABASES['mysql']
        conn = MySQLdb.connect(
            host=mysql_config['HOST'],
            port=int(mysql_config.get('PORT', 3306)),
            user=mysql_config['USER'],
            passwd=mysql_config['PASSWORD'],
            db=base,
            charset='latin1',
        )
        cursor = conn.cursor()

        columns_to_add = [
            ('ultimo_error_confirmacion', 'VARCHAR(512) DEFAULT NULL COMMENT "Mensaje del último fallo al confirmar"'),
            ('ultimo_intento_confirmacion', 'DATETIME DEFAULT NULL COMMENT "Timestamp del último intento fallido"'),
        ]
        for col_name, col_def in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE self_checkout_cart ADD COLUMN {col_name} {col_def}")
                self.stdout.write(self.style.SUCCESS(f'  Columna {col_name} agregada'))
            except MySQLdb.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    self.stdout.write(f'  Columna {col_name} ya existe, omitiendo')
                else:
                    raise
        conn.commit()
        cursor.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS('Migración 004 aplicada'))
