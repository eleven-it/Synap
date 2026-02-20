"""
Registra un kiosco en self_checkout_kiosk.
Uso: python manage.py seed_self_checkout_kiosk kiosk-01 --sucursal 1 --pv 1 --deposito 1 [--base-empresa X]

Valida que sucursal, pv y deposito existan en AdministraNET antes de insertar.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import MySQLdb


def _validar_ids(cursor, base: str, id_sucursal: int, id_pv: int, id_deposito: int) -> list:
    """Valida que los IDs existan. Retorna lista de errores (vacía si ok)."""
    errores = []
    try:
        cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name='sucursales'", [base])
        if cursor.fetchone():
            cursor.execute("SELECT 1 FROM sucursales WHERE id_sucursal = %s", [id_sucursal])
            if not cursor.fetchone():
                errores.append(f"sucursal {id_sucursal} no existe")
    except Exception:
        pass
    try:
        cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name='punto_venta'", [base])
        if cursor.fetchone():
            cursor.execute("SELECT 1 FROM punto_venta WHERE id_punto_venta = %s", [id_pv])
            if not cursor.fetchone():
                errores.append(f"punto_venta {id_pv} no existe")
    except Exception:
        pass
    try:
        found = False
        cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name='stock_deposito'", [base])
        if cursor.fetchone():
            cursor.execute("SELECT 1 FROM stock_deposito WHERE id_deposito = %s LIMIT 1", [id_deposito])
            if cursor.fetchone():
                found = True
        if not found:
            cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name='deposito'", [base])
            if cursor.fetchone():
                try:
                    cursor.execute("SELECT 1 FROM deposito WHERE CodDeposito = %s", [id_deposito])
                    if cursor.fetchone():
                        found = True
                except Exception:
                    pass
        if not found:
            errores.append(f"deposito {id_deposito} no existe")
    except Exception:
        pass
    return errores


class Command(BaseCommand):
    help = 'Registra kiosco en self_checkout_kiosk y valida IDs de sucursal/pv/deposito'

    def add_arguments(self, parser):
        parser.add_argument('kiosk_id', type=str)
        parser.add_argument('--sucursal', type=int, required=True)
        parser.add_argument('--pv', '--punto-venta', dest='pv', type=int, required=True)
        parser.add_argument('--deposito', type=int, required=True)
        parser.add_argument('--base-empresa', type=str, default=None)
        parser.add_argument('--modo-rfid', type=str, default='delta')
        parser.add_argument('--skip-validate', action='store_true', help='Omitir validación de IDs')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        kiosk_id = options['kiosk_id']
        id_sucursal = options['sucursal']
        id_pv = options['pv']
        id_deposito = options['deposito']
        modo_rfid = options['modo_rfid']
        skip_validate = options.get('skip_validate', False)

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

            if not skip_validate:
                errores = _validar_ids(cursor, base, id_sucursal, id_pv, id_deposito)
                if errores:
                    for e in errores:
                        self.stderr.write(self.style.WARNING(f'Validación: {e}'))
                    self.stderr.write(self.style.ERROR('Use --skip-validate para omitir validación.'))
                    conn.close()
                    return

            cursor.execute("""
                INSERT INTO self_checkout_kiosk (kiosk_id, id_sucursal, id_punto_venta, id_deposito, modo_rfid)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE id_sucursal=%s, id_punto_venta=%s, id_deposito=%s, modo_rfid=%s
            """, [kiosk_id, id_sucursal, id_pv, id_deposito, modo_rfid, id_sucursal, id_pv, id_deposito, modo_rfid])
            conn.commit()
            cursor.execute(
                "SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, activo FROM self_checkout_kiosk WHERE kiosk_id = %s",
                [kiosk_id],
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            self.stdout.write(self.style.SUCCESS(f'Kiosco {kiosk_id} configurado en {base}'))
            if row:
                self.stdout.write(f'  kiosk_id={row[0]} sucursal={row[1]} pv={row[2]} deposito={row[3]} activo={row[4]}')
        except MySQLdb.Error as e:
            self.stderr.write(self.style.ERROR(f'Error: {e}'))
