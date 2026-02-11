"""
Aplica migración 008: columnas serie/desc_serie en self_checkout_cart_item
y tabla self_checkout_cart_item_serie (números de serie por ítem).

Uso: python manage.py self_checkout_apply_migration_008 --base-empresa <NOMBRE>
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Aplica migración 008: series en cart_item y tabla cart_item_serie'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, default=None,
                            help='Nombre de la base de datos de la empresa')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        self.stdout.write(f'Aplicando migración 008 en base: {base}')

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
                f"La tabla self_checkout_cart_item no existe en la base '{base}'."
            ))
            raise SystemExit(1)

        for col_name, col_def in [
            ('serie', "VARCHAR(8) DEFAULT NULL COMMENT 'Si/No artículo seriado'"),
            ('desc_serie', "VARCHAR(500) DEFAULT NULL COMMENT 'Resumen números de serie'"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE self_checkout_cart_item ADD COLUMN {col_name} {col_def}")
                self.stdout.write(self.style.SUCCESS(f'  self_checkout_cart_item.{col_name} agregada'))
            except MySQLdb.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    self.stdout.write(f'  self_checkout_cart_item.{col_name} ya existe, omitiendo')
                else:
                    raise

        cursor.execute("""
            SELECT TABLE_NAME FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'self_checkout_cart_item_serie'
        """, [base])
        if cursor.fetchone():
            self.stdout.write('  self_checkout_cart_item_serie ya existe, omitiendo')
        else:
            cursor.execute("""
                CREATE TABLE self_checkout_cart_item_serie (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    cart_item_id BIGINT NOT NULL,
                    id_serie_entrada BIGINT NOT NULL,
                    nro_serie VARCHAR(128) DEFAULT NULL,
                    desc_serie VARCHAR(255) DEFAULT NULL,
                    vto_serie DATE DEFAULT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_cart_item (cart_item_id),
                    INDEX idx_serie_entrada (id_serie_entrada)
                ) ENGINE=InnoDB DEFAULT CHARSET=latin1
            """)
            self.stdout.write(self.style.SUCCESS('  Tabla self_checkout_cart_item_serie creada'))

        conn.commit()
        cursor.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS('Migración 008 aplicada'))
