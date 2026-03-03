"""
Aplica migración 007: columnas de voucher/programa de descuentos en self_checkout_cart
(id_sp_cupon, monto_descuento_voucher) como TPV VB6.

Uso: python manage.py self_checkout_apply_migration_007 --base-empresa <NOMBRE>
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Aplica migración 007: columnas id_sp_cupon, monto_descuento_voucher en cart'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, default=None,
                            help='Nombre de la base de datos de la empresa')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        self.stdout.write(f'Aplicando migración 007 en base: {base}')

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
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'self_checkout_cart'
        """, [base])
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            self.stderr.write(self.style.ERROR(
                f"La tabla self_checkout_cart no existe en la base '{base}'. "
                "Creá las tablas con: python manage.py create_self_checkout_tables --base-empresa " + base
            ))
            raise SystemExit(1)

        columns = [
            ('id_sp_cupon', "BIGINT DEFAULT NULL COMMENT 'FK sp_cupon_cliente.id_sp_cupon' AFTER id_cliente"),
            ('monto_descuento_voucher', "DECIMAL(18,4) DEFAULT NULL COMMENT '% descuento voucher al pie' AFTER id_sp_cupon"),
        ]
        for col_name, col_def in columns:
            try:
                cursor.execute(f"ALTER TABLE self_checkout_cart ADD COLUMN {col_name} {col_def}")
                self.stdout.write(self.style.SUCCESS(f'  self_checkout_cart.{col_name} agregada'))
            except MySQLdb.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    self.stdout.write(f'  self_checkout_cart.{col_name} ya existe, omitiendo')
                else:
                    raise

        conn.commit()
        cursor.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS('Migración 007 aplicada'))
