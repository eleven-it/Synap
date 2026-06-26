"""Vincular productos Tiendanube con artículos AdministraNET."""

from django.core.management.base import BaseCommand, CommandError

from tiendanube_administranet.models import AdministraNETConfig, TiendanubeConfig
from tiendanube_administranet.services.product_mapping_link import (
    link_products_from_tiendanube_order,
    link_tiendanube_product_to_adminet,
)


class Command(BaseCommand):
    help = (
        'Vincula un producto/variante TN con un IDArt Adminet, o todas las líneas '
        'de una orden TN (--from-order).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--tn-product-id', type=int, help='ID producto Tiendanube')
        parser.add_argument('--tn-variant-id', type=int, help='ID variante Tiendanube')
        parser.add_argument('--adminet-id', type=int, help='IDArt AdministraNET')
        parser.add_argument(
            '--from-order',
            type=int,
            help='ID orden TN: vincula cada línea con los --adminet-id dados (ordenados)',
        )
        parser.add_argument(
            '--adminet-ids',
            type=str,
            help='Lista de IDArt separados por coma (con --from-order)',
        )

    def handle(self, *args, **options):
        tn_cfg = TiendanubeConfig.objects.filter(is_active=True).first()
        ad_cfg = AdministraNETConfig.objects.filter(is_active=True).first()
        if not tn_cfg or not ad_cfg:
            raise CommandError('Falta TiendanubeConfig o AdministraNETConfig activa.')

        if options.get('from_order'):
            raw = (options.get('adminet_ids') or '').strip()
            if not raw:
                raise CommandError('Use --adminet-ids con --from-order (ej. 11252,11616).')
            adminet_ids = [int(x.strip()) for x in raw.split(',') if x.strip()]
            result = link_products_from_tiendanube_order(
                tiendanube_config=tn_cfg,
                adminet_config=ad_cfg,
                order_id=options['from_order'],
                adminet_ids=adminet_ids,
            )
        else:
            required = ('tn_product_id', 'tn_variant_id', 'adminet_id')
            if not all(options.get(k) for k in required):
                raise CommandError(
                    'Indique --tn-product-id, --tn-variant-id y --adminet-id '
                    'o use --from-order con --adminet-ids.'
                )
            result = link_tiendanube_product_to_adminet(
                tiendanube_config=tn_cfg,
                adminet_config=ad_cfg,
                tiendanube_product_id=options['tn_product_id'],
                tiendanube_variant_id=options['tn_variant_id'],
                adminet_id=options['adminet_id'],
            )

        if result.get('results'):
            for item in result['results']:
                msg = str(item)
                if item.get('success'):
                    self.stdout.write(self.style.SUCCESS(msg))
                else:
                    self.stdout.write(self.style.ERROR(msg))
        else:
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS(result.get('message', 'OK')))
            else:
                raise CommandError(result.get('message', 'Error al vincular'))

        if not result.get('success'):
            raise CommandError(result.get('message', 'Vinculación incompleta'))
