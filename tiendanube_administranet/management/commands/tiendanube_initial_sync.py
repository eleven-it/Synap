from django.core.management.base import BaseCommand, CommandError

from tiendanube_administranet.models import InitialSyncCheckpoint
from tiendanube_administranet.services.initial_sync_service import InitialSyncService


class Command(BaseCommand):
    help = (
        'Sync masiva inicial AdministraNET → Tienda Nube por lotes '
        '(resumible vía checkpoint).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            choices=['customer', 'product', 'both'],
            default='customer',
            help='Tipo de sync inicial (default: customer)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=30,
            help='Cantidad de ítems por lote (default: 30)',
        )
        parser.add_argument(
            '--offset',
            type=int,
            default=0,
            help='Desplazamiento manual (ignorado con --resume)',
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Continuar desde el último checkpoint guardado',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reinicia checkpoint antes de ejecutar (solo tipos seleccionados)',
        )

    def handle(self, *args, **options):
        tipo = options['tipo']
        batch_size = options['batch_size']
        offset = options['offset']
        resume = options['resume']
        reset = options['reset']

        if batch_size < 1:
            raise CommandError('batch-size debe ser >= 1')

        try:
            service = InitialSyncService()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        tipos = (
            [InitialSyncCheckpoint.SyncType.CUSTOMER, InitialSyncCheckpoint.SyncType.PRODUCT]
            if tipo == 'both'
            else [tipo]
        )

        if reset:
            for sync_type in tipos:
                service.reset_checkpoint(sync_type)
                self.stdout.write(self.style.WARNING(f'Checkpoint reiniciado: {sync_type}'))

        for sync_type in tipos:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sync inicial {sync_type} — lote de {batch_size} ítems'
                )
            )

            if resume:
                result = service.run_next_pending_batch(sync_type=sync_type, limit=batch_size)
            elif sync_type == InitialSyncCheckpoint.SyncType.PRODUCT:
                result = service.run_product_batch(limit=batch_size, offset=offset)
            else:
                result = service.run_customer_batch(limit=batch_size, offset=offset)

            self._print_result(sync_type, result)

            if not result.get('success'):
                raise CommandError(result.get('message') or result.get('error') or 'Error desconocido')

    def _print_result(self, sync_type: str, result: dict) -> None:
        self.stdout.write(f'  Tipo: {sync_type}')
        self.stdout.write(f'  Offset lote: {result.get("offset", "-")}')
        self.stdout.write(f'  Procesados: {result.get("total_processed", 0)}')
        self.stdout.write(f'  Exitosos: {result.get("successful", 0)}')
        self.stdout.write(f'  Fallidos: {result.get("failed", 0)}')
        self.stdout.write(f'  Total catálogo: {result.get("total_items", 0)}')
        self.stdout.write(f'  Último offset: {result.get("last_offset", 0)}')
        self.stdout.write(f'  Estado checkpoint: {result.get("checkpoint_status", "-")}')
        self.stdout.write(f'  Quedan lotes: {"Sí" if result.get("has_more") else "No"}')
        if result.get('sync_log_id'):
            self.stdout.write(f'  SyncLog ID: {result["sync_log_id"]}')
