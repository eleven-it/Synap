"""
Aplica migración 006: columnas de promoción por artículo en self_checkout_cart_item
(promocion_por, promocion_tipo, promocion_cant) para persistir en stock como TPV VB6.

Uso: python manage.py self_checkout_apply_migration_006 --base-empresa <NOMBRE>
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Aplica migración 006: columnas promocion_por, promocion_tipo, promocion_cant en cart_item'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, default=None,
                            help='Nombre de la base de datos de la empresa')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        self.stdout.write(f'Aplicando migración 006 en base: {base}')

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

        cursor.execute("""
            SELECT TABLE_NAME FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'self_checkout_cart_item'
        """, [base])
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            self.stderr.write(self.style.ERROR(
                f"La tabla self_checkout_cart_item no existe en la base '{base}'. "
                "Creá las tablas con: python manage.py create_self_checkout_tables --base-empresa " + base
            ))
            raise SystemExit(1)

        columns = [
            ('promocion_por', "DECIMAL(18,4) DEFAULT NULL COMMENT 'Promoción % o monto' AFTER promocion"),
            ('promocion_tipo', "VARCHAR(64) DEFAULT NULL COMMENT 'Monto fijo, Importe descuento, Cantidad, etc.' AFTER promocion_por"),
            ('promocion_cant', "DECIMAL(18,4) DEFAULT NULL COMMENT 'Cantidad mínima promo' AFTER promocion_tipo"),
        ]
        for col_name, col_def in columns:
            try:
                cursor.execute(f"ALTER TABLE self_checkout_cart_item ADD COLUMN {col_name} {col_def}")
                self.stdout.write(self.style.SUCCESS(f'  self_checkout_cart_item.{col_name} agregada'))
            except MySQLdb.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    self.stdout.write(f'  self_checkout_cart_item.{col_name} ya existe, omitiendo')
                else:
                    raise

        conn.commit()
        cursor.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS('Migración 006 aplicada'))
