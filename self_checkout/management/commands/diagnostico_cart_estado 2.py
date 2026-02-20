"""
Diagnóstico: Carritos con comprobante emitido pero estado pago_aprobado.
Ejecuta consultas en la DB para identificar inconsistencias.
Uso: python manage.py diagnostico_cart_estado [--base-empresa X] [--cart-id N]
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from self_checkout.db import mysql_cursor


class Command(BaseCommand):
    help = 'Diagnostica inconsistencias: carritos con invoice pero estado != confirmado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            help='Base de datos MySQL (default: DB_NAME de settings)',
        )
        parser.add_argument(
            '--cart-id',
            type=int,
            help='ID del carrito específico (ej: 121). Sin esto, lista todos los inconsistentes.',
        )

    def handle(self, *args, **options):
        base = (
            options.get('base_empresa')
            or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        )
        cart_id = options.get('cart_id')
        self.stdout.write(f'Base empresa: {base}')
        self.stdout.write('')

        try:
            if cart_id:
                self._diagnose_cart(base, cart_id)
            else:
                self._list_inconsistent(base)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            raise

    def _diagnose_cart(self, base: str, cart_id: int):
        """Diagnóstico detallado para un carrito."""
        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute(
                """
                SELECT id, estado, codigo_movimiento, id_cuentacliente, tipo_comprobante,
                       confirmed_at, created_at, total, kiosk_id, email
                FROM self_checkout_cart
                WHERE id = %s
                """,
                [cart_id],
            )
            cart = c.fetchone()

        if not cart:
            self.stdout.write(self.style.WARNING(f'Carrito {cart_id} no encontrado.'))
            return

        self.stdout.write('=== CART ===')
        for k, v in cart.items():
            self.stdout.write(f'  {k}: {v}')
        self.stdout.write('')

        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute(
                """
                SELECT id, cart_id, codigo_movimiento, id_cuentacliente, nro_comprobante,
                       tipo_comprobante, estado, cae, vto_cae, fe_regimen
                FROM self_checkout_invoice
                WHERE cart_id = %s
                """,
                [cart_id],
            )
            invoice = c.fetchone()

        self.stdout.write('=== INVOICE ===')
        if invoice:
            for k, v in invoice.items():
                self.stdout.write(f'  {k}: {v}')
            self.stdout.write('')
        else:
            self.stdout.write('  (no hay registro)')
            self.stdout.write('')

        cod_mov = cart.get('codigo_movimiento')
        if cod_mov is None and invoice:
            cod_mov = invoice.get('codigo_movimiento')
        if cod_mov:
            try:
                with mysql_cursor(base, dict_cursor=True) as c:
                    # cuentacliente: columnas pueden variar por versión administraNET
                    c.execute(
                        """
                        SELECT id_cuentacliente, CodigoMovimiento, NroComprobante, TipoComprobante,
                               fe_cae, fe_transmitido, fe_comp
                        FROM cuentacliente
                        WHERE CodigoMovimiento = %s
                        LIMIT 1
                        """,
                        [cod_mov],
                    )
                    cc = c.fetchone()
                self.stdout.write('=== CUENTACLIENTE ===')
                if cc:
                    for k, v in cc.items():
                        self.stdout.write(f'  {k}: {v}')
                else:
                    self.stdout.write('  (no encontrado)')
                self.stdout.write('')
            except Exception as e:
                self.stdout.write('=== CUENTACLIENTE ===')
                self.stdout.write(f'  (no se pudo consultar: {e})')
                self.stdout.write('')

        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute(
                """
                SELECT id, cart_id, accion, detalle, created_at
                FROM self_checkout_audit_log
                WHERE cart_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                [cart_id],
            )
            logs = c.fetchall()

        self.stdout.write('=== AUDIT LOG (últimos 5) ===')
        for log in logs:
            self.stdout.write(f"  {log['created_at']} | {log['accion']} | {log.get('detalle', '')[:80]}...")
        if not logs:
            self.stdout.write('  (ninguno)')
        self.stdout.write('')

        # Conclusión
        estado_cart = (cart.get('estado') or '').strip()
        tiene_invoice = invoice is not None
        tiene_cae = bool(invoice and invoice.get('cae'))

        if estado_cart != 'confirmado' and tiene_invoice and tiene_cae:
            self.stdout.write(
                self.style.ERROR(
                    '*** INCONSISTENCIA CONFIRMADA: Cart tiene invoice con CAE pero estado = '
                    f'"{estado_cart}". Debe estar "confirmado". ***'
                )
            )
            self.stdout.write('')
            self.stdout.write('Para corregir ejecutá:')
            self.stdout.write(
                f'  UPDATE self_checkout_cart sc '
                f'  INNER JOIN self_checkout_invoice si ON si.cart_id = sc.id '
                f'SET sc.estado = "confirmado", '
                f'sc.codigo_movimiento = si.codigo_movimiento, '
                f'sc.id_cuentacliente = si.id_cuentacliente, '
                f'sc.tipo_comprobante = si.tipo_comprobante, '
                f'sc.confirmed_at = COALESCE(sc.confirmed_at, NOW()) '
                f'WHERE sc.id = {cart_id};'
            )
        elif estado_cart == 'confirmado':
            self.stdout.write(self.style.SUCCESS('Estado correcto: confirmado'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Estado cart: {estado_cart}. Invoice: {"sí" if tiene_invoice else "no"}. '
                    f'CAE: {"sí" if tiene_cae else "no"}'
                )
            )

    def _list_inconsistent(self, base: str):
        """Lista todos los carritos con inconsistencia (tienen invoice pero estado != confirmado)."""
        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute(
                """
                SELECT sc.id AS cart_id, sc.estado AS cart_estado, sc.codigo_movimiento AS cart_cod_mov,
                       sc.id_cuentacliente AS cart_id_cc, sc.created_at,
                       si.nro_comprobante, si.tipo_comprobante, si.cae
                FROM self_checkout_cart sc
                INNER JOIN self_checkout_invoice si ON si.cart_id = sc.id
                WHERE sc.estado != 'confirmado'
                ORDER BY sc.id DESC
                LIMIT 50
                """
            )
            rows = c.fetchall()

        self.stdout.write('=== Carritos INCONSISTENTES (tienen invoice pero estado != confirmado) ===')
        self.stdout.write('')

        if not rows:
            self.stdout.write(self.style.SUCCESS('No se encontraron inconsistencias.'))
            return

        self.stdout.write(self.style.WARNING(f'Encontrados: {len(rows)}'))
        self.stdout.write('')
        for r in rows:
            self.stdout.write(
                f"  cart_id={r['cart_id']} estado={r['cart_estado']} "
                f"nro_comp={r['nro_comprobante']} cae={'sí' if r.get('cae') else 'no'} "
                f"created={r['created_at']}"
            )
        self.stdout.write('')
        self.stdout.write('Para corregir todos:')
        self.stdout.write(
            '  UPDATE self_checkout_cart sc '
            'INNER JOIN self_checkout_invoice si ON si.cart_id = sc.id '
            'SET sc.estado = "confirmado", '
            'sc.codigo_movimiento = COALESCE(si.codigo_movimiento, sc.codigo_movimiento), '
            'sc.id_cuentacliente = COALESCE(si.id_cuentacliente, sc.id_cuentacliente), '
            'sc.tipo_comprobante = COALESCE(si.tipo_comprobante, sc.tipo_comprobante), '
            'sc.confirmed_at = COALESCE(sc.confirmed_at, NOW()) '
            'WHERE sc.estado != "confirmado";'
        )
        self.stdout.write('')
        self.stdout.write('Para diagnóstico detallado de un carrito:')
        self.stdout.write('  python manage.py diagnostico_cart_estado --cart-id 121')
