"""
Reintenta confirmación para carritos en pago_aprobado (cobro en MP pero sin comprobante emitido).
Uso: python manage.py self_checkout_confirm_pending [--base-empresa X] [--limit N] [--days D] [--dry-run]
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.conf import settings

from self_checkout.db import mysql_cursor
from self_checkout.services.confirmation_service import ConfirmationService
from self_checkout.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reintenta confirmación para carritos en pago_aprobado (pago en MP sin comprobante emitido)'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, help='Base de datos (MySQL)')
        parser.add_argument('--limit', type=int, default=50, help='Máximo carritos a procesar')
        parser.add_argument('--days', type=int, default=30, help='Solo carritos creados en los últimos N días')
        parser.add_argument('--dry-run', action='store_true', help='Solo listar, no confirmar')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        limit = options.get('limit', 50)
        days = options.get('days', 30)
        dry_run = options.get('dry_run', False)

        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute("""
                SELECT id, kiosk_id, id_sucursal, id_punto_venta, total, id_cliente, email, cuit, tipo_comprobante, created_at
                FROM self_checkout_cart
                WHERE estado = 'pago_aprobado'
                AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                ORDER BY created_at ASC
                LIMIT %s
            """, [days, limit])
            rows = c.fetchall()

        if not rows:
            self.stdout.write('No hay carritos en pago_aprobado pendientes de confirmar.')
            return

        self.stdout.write(f'Carritos en pago_aprobado (últimos {days} días): {len(rows)}')
        if dry_run:
            for r in rows:
                self.stdout.write(
                    f"  cart_id={r['id']} kiosk={r['kiosk_id']} total={r['total']} created={r['created_at']}"
                )
            return

        conf_svc = ConfirmationService(base)
        inv_svc = InvoiceService(base)
        ok_count = 0
        for row in rows:
            cart_id = row['id']
            id_cliente = row['id_cliente'] or 1
            email = (row['email'] or '').strip() or 'noreply@autoconfirm.local'
            cuit = (row['cuit'] or '').strip() or None
            tipo_comp = inv_svc.determinar_tipo_comprobante(id_cliente, cuit)

            ok, error_msg, result = conf_svc.confirmar(
                cart_id=cart_id,
                id_cliente=id_cliente,
                email=email,
                tipo_comprobante=tipo_comp,
                cuit=cuit,
                id_usuario=0,
            )
            if not ok:
                self.stdout.write(self.style.WARNING(f"  cart_id={cart_id}: {error_msg}"))
                continue

            estado_fe = result.get('estado_fe') or 'pendiente'
            inv_svc.guardar_invoice(
                cart_id=cart_id,
                codigo_movimiento=result['codigo_movimiento'],
                id_cuentacliente=result['id_cuentacliente'],
                nro_comprobante=result['nro_comprobante'],
                tipo_comprobante=result['tipo_comprobante'],
                estado=estado_fe,
                cae=result.get('cae'),
                vto_cae=result.get('vto_cae'),
                fe_regimen=result.get('fe_regimen'),
            )
            # Caja: se registra dentro de confirmar (transacción atómica)
            ok_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  cart_id={cart_id} confirmado ok cod_mov={result.get('codigo_movimiento')} nro_comp={result.get('nro_comprobante')}"
                )
            )

        self.stdout.write(self.style.SUCCESS(f'Confirmados: {ok_count} de {len(rows)}'))
