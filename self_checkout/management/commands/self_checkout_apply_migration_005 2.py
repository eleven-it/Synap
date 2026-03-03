"""
Aplica migración 005: columnas TPV en self_checkout_cart_item (codigo_barras, porcentaje_descuento, promocion, detalle)
y modo_tpv en self_checkout_kiosk.
Uso: python manage.py self_checkout_apply_migration_005 --base-empresa <NOMBRE>
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Aplica migración 005: columnas TPV en cart_item y kiosk (grilla extendida y modo TPV)'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, default=None,
                            help='Nombre de la base de datos de la empresa')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        self.stdout.write(f'Aplicando migración 005 en base: {base}')

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

        # Verificar que existan las tablas base (creadas con create_self_checkout_tables)
        cursor.execute("""
            SELECT TABLE_NAME FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ('self_checkout_cart_item', 'self_checkout_kiosk')
        """, [base])
        existing = {row[0] for row in cursor.fetchall()}
        if 'self_checkout_cart_item' not in existing or 'self_checkout_kiosk' not in existing:
            cursor.close()
            conn.close()
            self.stderr.write(self.style.ERROR(
                f"Las tablas self_checkout_* no existen en la base '{base}'. "
                "Creálas primero con:\n  python manage.py create_self_checkout_tables --base-empresa " + base
            ))
            raise SystemExit(1)

        cart_item_columns = [
            ('codigo_barras', 'VARCHAR(64) DEFAULT NULL COMMENT "Código de barra" AFTER codigo_articulo'),
            ('porcentaje_descuento', 'DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT "% descuento renglón" AFTER importe_total'),
            ('promocion', 'VARCHAR(255) DEFAULT NULL COMMENT "Promoción" AFTER porcentaje_descuento'),
            ('detalle', 'TEXT DEFAULT NULL COMMENT "Detalle renglón" AFTER promocion'),
        ]
        for col_name, col_def in cart_item_columns:
            try:
                cursor.execute(f"ALTER TABLE self_checkout_cart_item ADD COLUMN {col_name} {col_def}")
                self.stdout.write(self.style.SUCCESS(f'  self_checkout_cart_item.{col_name} agregada'))
            except MySQLdb.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    self.stdout.write(f'  self_checkout_cart_item.{col_name} ya existe, omitiendo')
                else:
                    raise

        try:
            cursor.execute("ALTER TABLE self_checkout_kiosk ADD COLUMN modo_tpv TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1=TPV' AFTER activo")
            self.stdout.write(self.style.SUCCESS('  self_checkout_kiosk.modo_tpv agregado'))
        except MySQLdb.OperationalError as e:
            if 'Duplicate column name' in str(e):
                self.stdout.write('  self_checkout_kiosk.modo_tpv ya existe, omitiendo')
            else:
                raise

        conn.commit()
        cursor.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS('Migración 005 aplicada'))
