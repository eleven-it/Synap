"""
Aplica migraciones 006 y 007 en una sola ejecución (promociones por artículo + voucher en carrito).

- 006: columnas promocion_por, promocion_tipo, promocion_cant en self_checkout_cart_item
- 007: columnas id_sp_cupon, monto_descuento_voucher en self_checkout_cart

Uso:
  python manage.py self_checkout_apply_migrations_promociones_voucher --base-empresa <NOMBRE>

Para todas las bases configuradas (si tenés varias empresas):
  python manage.py self_checkout_apply_migrations_promociones_voucher --all-bases
"""
from django.core.management.base import BaseCommand
from django.conf import settings


def apply_006(cursor, base: str, stdout, style):
    """Migración 006: cart_item promocion_por, promocion_tipo, promocion_cant."""
    cursor.execute("""
        SELECT TABLE_NAME FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'self_checkout_cart_item'
    """, [base])
    if not cursor.fetchone():
        return False, "self_checkout_cart_item no existe"
    columns = [
        ('promocion_por', "DECIMAL(18,4) DEFAULT NULL COMMENT 'Promoción % o monto' AFTER promocion"),
        ('promocion_tipo', "VARCHAR(64) DEFAULT NULL COMMENT 'Monto fijo, Importe descuento, Cantidad, etc.' AFTER promocion_por"),
        ('promocion_cant', "DECIMAL(18,4) DEFAULT NULL COMMENT 'Cantidad mínima promo' AFTER promocion_tipo"),
    ]
    for col_name, col_def in columns:
        try:
            cursor.execute(f"ALTER TABLE self_checkout_cart_item ADD COLUMN {col_name} {col_def}")
            stdout.write(style.SUCCESS(f'  [006] self_checkout_cart_item.{col_name} agregada'))
        except Exception as e:
            if 'Duplicate column name' in str(e):
                stdout.write(f'  [006] self_checkout_cart_item.{col_name} ya existe')
            else:
                raise
    return True, None


def apply_007(cursor, base: str, stdout, style):
    """Migración 007: cart id_sp_cupon, monto_descuento_voucher."""
    cursor.execute("""
        SELECT TABLE_NAME FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'self_checkout_cart'
    """, [base])
    if not cursor.fetchone():
        return False, "self_checkout_cart no existe"
    columns = [
        ('id_sp_cupon', "BIGINT DEFAULT NULL COMMENT 'FK sp_cupon_cliente.id_sp_cupon' AFTER id_cliente"),
        ('monto_descuento_voucher', "DECIMAL(18,4) DEFAULT NULL COMMENT '% descuento voucher al pie' AFTER id_sp_cupon"),
    ]
    for col_name, col_def in columns:
        try:
            cursor.execute(f"ALTER TABLE self_checkout_cart ADD COLUMN {col_name} {col_def}")
            stdout.write(style.SUCCESS(f'  [007] self_checkout_cart.{col_name} agregada'))
        except Exception as e:
            if 'Duplicate column name' in str(e):
                stdout.write(f'  [007] self_checkout_cart.{col_name} ya existe')
            else:
                raise
    return True, None


class Command(BaseCommand):
    help = 'Aplica migraciones 006 y 007 (promociones + voucher) en la base indicada o en todas'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, default=None,
                            help='Nombre de la base de datos de la empresa')
        parser.add_argument('--all-bases', action='store_true',
                            help='Aplicar en todas las bases listadas en MULTI_DATABASE_EMPRESAS (si existe)')

    def handle(self, *args, **options):
        try:
            import MySQLdb
        except ImportError:
            self.stderr.write(self.style.ERROR('Instalar: pip install mysqlclient'))
            raise SystemExit(1)

        bases = []
        if options.get('all_bases'):
            multi = getattr(settings, 'MULTI_DATABASE_EMPRESAS', None)
            if multi and isinstance(multi, (list, tuple)):
                bases = list(multi)
            else:
                self.stderr.write(self.style.WARNING(
                    '--all-bases requiere MULTI_DATABASE_EMPRESAS en settings. Usá --base-empresa <NOMBRE>.'
                ))
                raise SystemExit(1)
        else:
            base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
            bases = [base]

        mysql_config = settings.DATABASES['mysql']
        for base in bases:
            self.stdout.write(f'Aplicando migraciones 006 y 007 en base: {base}')
            conn = MySQLdb.connect(
                host=mysql_config['HOST'],
                port=int(mysql_config.get('PORT', 3306)),
                user=mysql_config['USER'],
                passwd=mysql_config['PASSWORD'],
                db=base,
                charset='latin1',
            )
            cursor = conn.cursor()
            try:
                ok_006, err_006 = apply_006(cursor, base, self.stdout, self.style)
                if not ok_006:
                    self.stdout.write(self.style.WARNING(f'  [006] Omitido: {err_006}'))
                ok_007, err_007 = apply_007(cursor, base, self.stdout, self.style)
                if not ok_007:
                    self.stdout.write(self.style.WARNING(f'  [007] Omitido: {err_007}'))
                conn.commit()
                self.stdout.write(self.style.SUCCESS(f'  Base {base}: listo'))
            finally:
                cursor.close()
                conn.close()
        self.stdout.write(self.style.SUCCESS('Migraciones 006 y 007 finalizadas'))
