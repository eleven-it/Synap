"""
Sync masiva inicial AdministraNET → Tienda Nube por lotes, resumible vía checkpoint.
"""

import logging
from typing import Any, Dict, Optional

from django.utils import timezone

from ..models import (
    AdministraNETConfig,
    InitialSyncCheckpoint,
    TiendanubeConfig,
)
from ..utils.feature_flags import tiendanube_sync_disabled_reason
from .sync_service import TiendanubeAdministraNETSyncService

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 30


class InitialSyncService:
    """Orquesta la sync inicial por lotes sin saturar la API de Tienda Nube."""

    def __init__(
        self,
        tiendanube_config: Optional[TiendanubeConfig] = None,
        adminet_config: Optional[AdministraNETConfig] = None,
        base_empresa: Optional[str] = None,
    ):
        self.tiendanube_config = tiendanube_config or TiendanubeConfig.objects.filter(
            is_active=True
        ).first()
        self.adminet_config = adminet_config or AdministraNETConfig.objects.filter(
            is_active=True
        ).first()
        if not self.tiendanube_config or not self.adminet_config:
            raise ValueError(
                'Se requiere configuración Tiendanube y AdministraNET activas.'
            )
        self._base_empresa = base_empresa
        self.sync_service = TiendanubeAdministraNETSyncService(
            self.tiendanube_config,
            self.adminet_config,
            base_empresa=base_empresa,
        )

    def _sync_disabled_response(self) -> Dict[str, Any]:
        reason = tiendanube_sync_disabled_reason(self.tiendanube_config)
        return {
            'success': False,
            'message': reason or 'Sincronización deshabilitada',
        }

    def _get_checkpoint(self, sync_type: str) -> InitialSyncCheckpoint:
        checkpoint, _ = InitialSyncCheckpoint.objects.get_or_create(
            sync_type=sync_type,
            tiendanube_config=self.tiendanube_config,
            adminet_config=self.adminet_config,
            defaults={
                'last_offset': 0,
                'total_items': 0,
                'status': InitialSyncCheckpoint.Status.PENDING,
            },
        )
        return checkpoint

    def _update_checkpoint(
        self,
        checkpoint: InitialSyncCheckpoint,
        result: Dict[str, Any],
        offset: int,
    ) -> InitialSyncCheckpoint:
        checkpoint.last_run_at = timezone.now()
        total_available = result.get('total_available', checkpoint.total_items)
        if total_available is not None:
            checkpoint.total_items = total_available

        if not result.get('success'):
            checkpoint.status = InitialSyncCheckpoint.Status.FAILED
            checkpoint.error_message = result.get('message', '') or result.get('error', '')
            checkpoint.save()
            return checkpoint

        processed = result.get('total_processed', 0)
        checkpoint.last_offset = offset + processed
        checkpoint.error_message = ''

        if checkpoint.last_offset >= checkpoint.total_items:
            checkpoint.status = InitialSyncCheckpoint.Status.COMPLETED
        else:
            checkpoint.status = InitialSyncCheckpoint.Status.IN_PROGRESS

        checkpoint.save()
        return checkpoint

    def _build_batch_response(
        self,
        sync_type: str,
        result: Dict[str, Any],
        checkpoint: InitialSyncCheckpoint,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        return {
            **result,
            'sync_type': sync_type,
            'offset': offset,
            'limit': limit,
            'last_offset': checkpoint.last_offset,
            'total_items': checkpoint.total_items,
            'checkpoint_status': checkpoint.status,
            'has_more': checkpoint.has_more,
            'checkpoint_id': checkpoint.id,
        }

    def run_customer_batch(self, limit: int = DEFAULT_BATCH_SIZE, offset: int = 0) -> Dict[str, Any]:
        """Procesa un lote de clientes Adminet → TN y persiste checkpoint."""
        if tiendanube_sync_disabled_reason(self.tiendanube_config):
            return self._sync_disabled_response()

        checkpoint = self._get_checkpoint(InitialSyncCheckpoint.SyncType.CUSTOMER)
        if checkpoint.status == InitialSyncCheckpoint.Status.COMPLETED and offset >= checkpoint.total_items:
            return {
                'success': True,
                'message': 'Sync inicial de clientes ya completada.',
                'sync_type': InitialSyncCheckpoint.SyncType.CUSTOMER,
                'offset': checkpoint.last_offset,
                'limit': limit,
                'last_offset': checkpoint.last_offset,
                'total_items': checkpoint.total_items,
                'checkpoint_status': checkpoint.status,
                'has_more': False,
                'checkpoint_id': checkpoint.id,
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
            }

        if checkpoint.status != InitialSyncCheckpoint.Status.IN_PROGRESS:
            checkpoint.status = InitialSyncCheckpoint.Status.IN_PROGRESS
            checkpoint.save(update_fields=['status'])

        result = self.sync_service.sync_customers_from_adminet(limit=limit, offset=offset)
        checkpoint = self._update_checkpoint(checkpoint, result, offset)
        return self._build_batch_response(
            InitialSyncCheckpoint.SyncType.CUSTOMER,
            result,
            checkpoint,
            offset,
            limit,
        )

    def run_product_batch(self, limit: int = DEFAULT_BATCH_SIZE, offset: int = 0) -> Dict[str, Any]:
        """Procesa un lote de productos Adminet → TN y persiste checkpoint."""
        if tiendanube_sync_disabled_reason(self.tiendanube_config):
            return self._sync_disabled_response()

        checkpoint = self._get_checkpoint(InitialSyncCheckpoint.SyncType.PRODUCT)
        if checkpoint.status == InitialSyncCheckpoint.Status.COMPLETED and offset >= checkpoint.total_items:
            return {
                'success': True,
                'message': 'Sync inicial de productos ya completada.',
                'sync_type': InitialSyncCheckpoint.SyncType.PRODUCT,
                'offset': checkpoint.last_offset,
                'limit': limit,
                'last_offset': checkpoint.last_offset,
                'total_items': checkpoint.total_items,
                'checkpoint_status': checkpoint.status,
                'has_more': False,
                'checkpoint_id': checkpoint.id,
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
            }

        if checkpoint.status != InitialSyncCheckpoint.Status.IN_PROGRESS:
            checkpoint.status = InitialSyncCheckpoint.Status.IN_PROGRESS
            checkpoint.save(update_fields=['status'])

        result = self.sync_service.sync_products_from_adminet(limit=limit, offset=offset)
        checkpoint = self._update_checkpoint(checkpoint, result, offset)
        return self._build_batch_response(
            InitialSyncCheckpoint.SyncType.PRODUCT,
            result,
            checkpoint,
            offset,
            limit,
        )

    def run_next_pending_batch(
        self,
        sync_type: str = InitialSyncCheckpoint.SyncType.CUSTOMER,
        limit: int = DEFAULT_BATCH_SIZE,
    ) -> Dict[str, Any]:
        """Lee offset desde checkpoint y ejecuta el siguiente lote pendiente."""
        checkpoint = self._get_checkpoint(sync_type)

        if checkpoint.status == InitialSyncCheckpoint.Status.COMPLETED:
            return {
                'success': True,
                'message': f'Sync inicial de {sync_type} ya completada.',
                'sync_type': sync_type,
                'offset': checkpoint.last_offset,
                'limit': limit,
                'last_offset': checkpoint.last_offset,
                'total_items': checkpoint.total_items,
                'checkpoint_status': checkpoint.status,
                'has_more': False,
                'checkpoint_id': checkpoint.id,
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
            }

        offset = checkpoint.last_offset
        if sync_type == InitialSyncCheckpoint.SyncType.PRODUCT:
            return self.run_product_batch(limit=limit, offset=offset)
        return self.run_customer_batch(limit=limit, offset=offset)

    def reset_checkpoint(
        self,
        sync_type: str,
    ) -> InitialSyncCheckpoint:
        """Reinicia progreso de sync inicial para un tipo."""
        checkpoint = self._get_checkpoint(sync_type)
        checkpoint.last_offset = 0
        checkpoint.total_items = 0
        checkpoint.status = InitialSyncCheckpoint.Status.PENDING
        checkpoint.error_message = ''
        checkpoint.last_run_at = None
        checkpoint.save()
        return checkpoint
