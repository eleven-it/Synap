"""
Añade la columna cod_viajante a self_checkout_kiosk en la base MySQL de la empresa.
Para bases creadas antes de incluir esta columna en el DDL.

Uso:
  python manage.py add_cod_viajante_kiosk --base-empresa <NOMBRE>
  python manage.py add_cod_viajante_kiosk --base-empresa administranet

Si la columna ya existe, se ignora (idempotente).
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Añade columna cod_viajante a self_checkout_kiosk en la base MySQL de la empresa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            default=None,
            help='Nombre de la base de datos de la empresa (ej: administranet).',
        )

    def handle(self, *args, **options):
        base_empresa = options.get('base_empresa')
        if not base_empresa:
            base_empresa = settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
            self.stdout.write(f'Usando base: {base_empresa}')

        mysql_config = settings.DATABASES.get('mysql')
        if not mysql_config:
            self.stderr.write(self.style.ERROR('No hay configuración MySQL en settings.DATABASES'))
            return

        alter_sql = """
        ALTER TABLE self_checkout_kiosk
        ADD COLUMN cod_viajante INT NULL DEFAULT NULL
        COMMENT 'FK viajantes.CodViajante - vendedor asignado al kiosco'
        AFTER id_deposito
        """
        try:
            import MySQLdb
            conn = MySQLdb.connect(
                host=mysql_config['HOST'],
                port=int(mysql_config.get('PORT', 3306)),
                user=mysql_config['USER'],
                passwd=mysql_config['PASSWORD'],
                db=base_empresa,
                charset='latin1',
            )
            cursor = conn.cursor()
            try:
                cursor.execute(alter_sql)
                conn.commit()
                self.stdout.write(self.style.SUCCESS(f'Base {base_empresa}: columna cod_viajante añadida a self_checkout_kiosk.'))
            except Exception as e:
                err = str(e).strip()
                if 'Duplicate column name' in err or '1060' in err:
                    self.stdout.write(f'Base {base_empresa}: cod_viajante ya existe en self_checkout_kiosk (nada que hacer).')
                else:
                    raise
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            err_msg = str(e)
            if 'MySQLdb' in err_msg or 'No module' in err_msg:
                self.stderr.write(self.style.ERROR('Instalar: pip install mysqlclient'))
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
