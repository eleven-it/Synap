"""
Crea las tablas self_checkout_* en la base de datos MySQL de una empresa.
Opera por base_empresa: cada empresa tiene su propia base (multi-tenant).

Uso:
  python manage.py create_self_checkout_tables --base-empresa <NOMBRE>
  python manage.py create_self_checkout_tables --base-empresa emp1 --dry-run

Si no se indica --base-empresa, usa DATABASES['mysql']['NAME'].
"""
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


def _strip_leading_comments(stmt):
    """Quita líneas de comentario al inicio para obtener SQL ejecutable."""
    lines = stmt.split('\n')
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith('--'):
            return '\n'.join(lines[i:]).strip()
    return ''


class Command(BaseCommand):
    help = 'Crea tablas self_checkout_* en la base MySQL de la empresa (por base_empresa)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            default=None,
            help='Nombre de la base de datos de la empresa (ej: mi_empresa_db). Obligatorio en multi-tenant.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar SQL sin ejecutar',
        )

    def handle(self, *args, **options):
        base_empresa = options.get('base_empresa')
        dry_run = options.get('dry_run')

        if not base_empresa:
            base_empresa = settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
            self.stdout.write(f'Usando base: {base_empresa}')

        sql_path = Path(__file__).resolve().parent.parent.parent / 'sql' / '001_self_checkout_tables.sql'
        if not sql_path.exists():
            self.stderr.write(self.style.ERROR(f'No se encontró {sql_path}'))
            return

        sql_content = sql_path.read_text(encoding='utf-8')
        raw_statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        statements = []
        for stmt in raw_statements:
            stmt = _strip_leading_comments(stmt)
            if stmt:
                statements.append(stmt)

        SCO_TABLES = [
            'self_checkout_kiosk', 'self_checkout_cart', 'self_checkout_cart_item',
            'self_checkout_payment_intent', 'self_checkout_invoice',
            'self_checkout_rfid_event', 'self_checkout_kiosk_session', 'self_checkout_audit_log',
        ]

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No se ejecutará'))
            for i, stmt in enumerate(statements, 1):
                preview = stmt[:150].replace('\n', ' ') + '...' if len(stmt) > 150 else stmt.replace('\n', ' ')
                self.stdout.write(f'  [{i}] {preview}')
            return

        mysql_config = settings.DATABASES['mysql']
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

            # Check: tablas existentes antes (idempotente)
            placeholders = ', '.join(['%s'] * len(SCO_TABLES))
            cursor.execute(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = %s AND table_name IN ({placeholders})",
                [base_empresa] + SCO_TABLES,
            )
            existed_before = {r[0] for r in cursor.fetchall()}

            # Ejecutar DDL (CREATE TABLE IF NOT EXISTS = idempotente)
            for i, stmt in enumerate(statements):
                if stmt:
                    try:
                        cursor.execute(stmt)
                    except Exception as ex:
                        self.stderr.write(self.style.ERROR(f'Statement [{i+1}] failed: {ex}'))
                        self.stderr.write(stmt[:500] + ('...' if len(stmt) > 500 else ''))
                        raise

            conn.commit()

            # Check: tablas después
            cursor.execute(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = %s AND table_name IN ({placeholders})",
                [base_empresa] + SCO_TABLES,
            )
            exists_after = {r[0] for r in cursor.fetchall()}
            created = exists_after - existed_before
            already_existed = existed_before & exists_after

            cursor.close()
            conn.close()

            # Reportar
            self.stdout.write(self.style.SUCCESS(f'Base: {base_empresa}'))
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Creadas: {", ".join(sorted(created))}'))
            if already_existed:
                self.stdout.write(f'  Ya existían: {", ".join(sorted(already_existed))}')
            if not created and not already_existed:
                self.stdout.write(self.style.WARNING('  No se crearon tablas (revisar conexión)'))
        except Exception as e:
            err_msg = str(e)
            if 'MySQLdb' in err_msg or 'No module' in err_msg:
                self.stderr.write(self.style.ERROR('Instalar: pip install mysqlclient'))
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
