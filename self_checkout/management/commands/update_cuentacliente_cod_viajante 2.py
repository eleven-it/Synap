"""
Actualiza CodViajante en facturas de Self-Checkout ya creadas (cuentacliente con tpv_comp = 'Si').

Uso:
  python manage.py update_cuentacliente_cod_viajante --base-empresa administranet --cod-viajante 2
  python manage.py update_cuentacliente_cod_viajante --base-empresa administranet --cod-viajante 2 --dry-run
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Actualiza CodViajante en facturas Self-Checkout (cuentacliente tpv_comp=Si)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            default=None,
            help='Nombre de la base de datos de la empresa (ej: administranet).',
        )
        parser.add_argument(
            '--cod-viajante',
            type=int,
            default=2,
            help='Código de viajante a asignar (default: 2).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar cuántos registros se actualizarían, sin modificar.',
        )

    def handle(self, *args, **options):
        base_empresa = options.get('base_empresa')
        cod_viajante = options.get('cod_viajante')
        dry_run = options.get('dry_run', False)
        if not base_empresa:
            base_empresa = settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
            self.stdout.write(f'Usando base: {base_empresa}')
        self.stdout.write(f'CodViajante a asignar: {cod_viajante}')

        mysql_config = settings.DATABASES.get('mysql')
        if not mysql_config:
            self.stderr.write(self.style.ERROR('No hay configuración MySQL en settings.DATABASES'))
            return

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
            # Solo facturas TPV con CodViajante NULL o 0
            cursor.execute(
                """
                SELECT COUNT(*) FROM cuentacliente
                WHERE tpv_comp = 'Si' AND (CodViajante IS NULL OR CodViajante = 0)
                """
            )
            count = cursor.fetchone()[0]
            if count == 0:
                self.stdout.write(f'No hay registros cuentacliente (tpv_comp=Si) con CodViajante NULL/0 en {base_empresa}.')
                cursor.close()
                conn.close()
                return
            if dry_run:
                self.stdout.write(self.style.WARNING(f'DRY RUN: se actualizarían {count} registro(s) a CodViajante = {cod_viajante}.'))
                cursor.close()
                conn.close()
                return
            cursor.execute(
                """
                UPDATE cuentacliente
                SET CodViajante = %s
                WHERE tpv_comp = 'Si' AND (CodViajante IS NULL OR CodViajante = 0)
                """,
                [cod_viajante],
            )
            conn.commit()
            updated = cursor.rowcount
            cursor.close()
            conn.close()
            self.stdout.write(self.style.SUCCESS(f'Base {base_empresa}: {updated} factura(s) Self-Checkout actualizadas a CodViajante = {cod_viajante}.'))
        except Exception as e:
            err_msg = str(e)
            if 'MySQLdb' in err_msg or 'No module' in err_msg:
                self.stderr.write(self.style.ERROR('Instalar: pip install mysqlclient'))
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
