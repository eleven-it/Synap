"""
Reintenta envío FE para facturas pendientes (issued_caea_pending, failed).
Uso: python manage.py self_checkout_retry_fe [--base-empresa X] [--limit N] [--dry-run]
"""
import logging
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.conf import settings

from self_checkout.fe_config import is_fe_configured, sanitize_for_log
from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reintenta FE para facturas issued_caea_pending o failed'

    def add_arguments(self, parser):
        parser.add_argument('--base-empresa', type=str, help='Base de datos')
        parser.add_argument('--limit', type=int, default=50, help='Máximo facturas a reintentar')
        parser.add_argument('--dry-run', action='store_true', help='Solo listar, no enviar')

    def handle(self, *args, **options):
        base = options.get('base_empresa') or settings.DATABASES.get('mysql', {}).get('NAME', 'administranet')
        limit = options.get('limit', 50)
        dry_run = options.get('dry_run', False)

        if not is_fe_configured(base):
            self.stderr.write('AFIP no configurado (cert/key/cuit).')
            return

        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute("""
                SELECT si.id, si.cart_id, si.codigo_movimiento, si.id_cuentacliente,
                       si.nro_comprobante, si.tipo_comprobante, si.estado, si.cae,
                       sc.id_punto_venta, sc.total, sc.subtotal, sc.id_cliente, sc.email
                FROM self_checkout_invoice si
                INNER JOIN self_checkout_cart sc ON sc.id = si.cart_id
                WHERE si.estado IN ('issued_caea_pending', 'failed')
                ORDER BY si.created_at ASC
                LIMIT %s
            """, [limit])
            rows = c.fetchall()

        if not rows:
            self.stdout.write('No hay facturas pendientes de reintento.')
            return

        self.stdout.write(f'Facturas a reintentar: {len(rows)}')
        if dry_run:
            for r in rows:
                self.stdout.write(f"  id={r['id']} cart={r['cart_id']} estado={r['estado']}")
            return

        from self_checkout.services.invoice_service import InvoiceService
        svc = InvoiceService(base)
        ok_count = 0
        for row in rows:
            estado, cae, vto_cae, err = svc.emitir_fe(
                cart_id=row['cart_id'],
                id_cuentacliente=row['id_cuentacliente'],
                codigo_movimiento=row['codigo_movimiento'],
                tipo_comprobante=row['tipo_comprobante'],
                nro_comprobante=row['nro_comprobante'],
                id_punto_venta=row['id_punto_venta'],
                total=Decimal(str(row['total'] or 0)),
                subtotal=Decimal(str(row['subtotal'] or 0)),
                id_cliente=row.get('id_cliente') or 1,
                cuit=None,
            )
            fe_reg = 'CAE' if estado == 'issued_cae' else ('CAEA' if estado in ('issued_caea_pending', 'sent') else None)
            svc.actualizar_invoice(
                row['id'],
                estado=estado,
                cae=cae,
                vto_cae=vto_cae,
                fe_regimen=fe_reg,
                error_msg=(err or {}).get('msg') if estado == 'failed' else None,
            )
            if estado in ('issued_cae', 'issued_caea_pending', 'sent'):
                svc.actualizar_cuentacliente_fe(
                    id_cuentacliente=row['id_cuentacliente'],
                    estado_fe=estado,
                    cae=cae,
                    vto_cae=vto_cae,
                    fe_regimen=fe_reg,
                )
                ok_count += 1
            self.stdout.write(f"  invoice {row['id']}: {estado}")

        self.stdout.write(self.style.SUCCESS(f'Reintentadas: {len(rows)}, exitosas: {ok_count}'))
