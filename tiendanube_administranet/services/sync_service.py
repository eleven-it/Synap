"""
Servicio principal de sincronización entre Tiendanube y AdministraNET.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from core.utils.administranet_types import str_or_default, to_int_or_none
from ..utils.feature_flags import tiendanube_sync_disabled_reason
from .customer_lookup import (
    nombre_completo_a_campos_tiendanube,
    tiendanube_customer_to_form_fields,
)
from .tiendanube_service import TiendanubeService
from .adminet_service import AdministraNETService
from .product_service import TiendanubeProductService
from .automatic_mapping_service import AutomaticMappingService
from .product_pricing import precios_tiendanube_desde_articulo
from .sync_change_detection import (
    actualizar_snapshot_cliente_adminet,
    actualizar_snapshot_cliente_tiendanube,
    cliente_adminet_cambio,
    cliente_tn_modificado,
    producto_requiere_sync_adminet_a_tn,
)
from ..models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping, 
    ProductMapping, ProductVariantMapping, OrderMapping, SyncLog
)

logger = logging.getLogger(__name__)

SYNC_SKIP_MINUTES = 5
STOCK_PRICE_BATCH_MAX = 50


def normalize_product_visibility_payload(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Contrato API 2026: enviar visibility XOR published (nunca ambos)."""
    payload = dict(product_data)
    if 'visibility' in payload:
        payload.pop('published', None)
        return payload
    if 'published' in payload:
        published = payload.pop('published')
        payload['visibility'] = 'visible' if published else 'hidden'
    return payload


def build_inventory_level_entry(
    stock: int,
    location_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Entrada inventory_levels para PATCH stock-price."""
    entry: Dict[str, Any] = {'stock': stock}
    if location_id is not None:
        entry['location_id'] = location_id
    return entry


class TiendanubeAdministraNETSyncService:
    """
    Servicio principal para sincronización bidireccional entre Tiendanube y AdministraNET.
    """

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
                "Se requiere configuración Tiendanube y AdministraNET activas."
            )
        be = (base_empresa or (self.adminet_config.database or "")).strip()
        if not be:
            raise ValueError(
                "Indique base_empresa o configure AdministraNETConfig.database."
            )
        self._base_empresa = be
        self.tiendanube_service = TiendanubeService(self.tiendanube_config)
        self.adminet_service = AdministraNETService(self.adminet_config, base_empresa=be)
        self.product_service = TiendanubeProductService(self.tiendanube_config)
        self.mapping_service = AutomaticMappingService(self.tiendanube_config, self.adminet_config)
        
        # Configurar webhooks automáticamente al inicializar
        self._ensure_webhooks_configured()
    
    def _complete_sync_with_status(self, sync_log, successful_syncs, failed_syncs, total_items):
        """
        Completar sincronización con lógica de estado correcta.
        
        Args:
            sync_log: Instancia del log de sincronización
            successful_syncs: Número de items exitosos
            failed_syncs: Número de items fallidos
            total_items: Total de items procesados
        """
        sync_log.successful_items = successful_syncs
        sync_log.failed_items = failed_syncs
        
        # Determinar si la sincronización fue exitosa
        if failed_syncs == total_items and successful_syncs == 0:
            # Todos los items fallaron
            sync_log.complete_sync(False, f"Todos los {failed_syncs} items fallaron en la sincronización")
        elif failed_syncs > 0:
            # Sincronización parcial - marcar como completada pero con advertencia
            sync_log.complete_sync(True)
            sync_log.error_message = f"Sincronización parcial: {successful_syncs} exitosas, {failed_syncs} fallidas"
            sync_log.save()
        else:
            # Sincronización completamente exitosa
            sync_log.complete_sync(True)
    
    def _ensure_webhooks_configured(self):
        """
        Asegurar que los webhooks estén configurados automáticamente.
        Se ejecuta la primera vez que se usa el sistema.
        """
        try:
            from .webhook_auto_config import WebhookAutoConfig
            
            webhook_config = WebhookAutoConfig(self.tiendanube_config)
            result = webhook_config.configure_all_webhooks()
            
            if result['success']:
                created = result.get('created', [])
                skipped = result.get('skipped', [])
                failed = result.get('failed', [])
                
                if created:
                    logger.info(f"✅ Webhooks creados automáticamente: {', '.join(created)}")
                if skipped:
                    logger.info(f"ℹ️  Webhooks ya existían: {', '.join(skipped)}")
                if failed:
                    logger.warning(f"⚠️  Webhooks fallidos: {len(failed)}")
                
                logger.info(f"🔗 URL base del webhook: {result.get('webhook_base_url')}")
                logger.info(f"📊 Total: {result.get('total_created')} creados, {result.get('total_skipped')} omitidos, {result.get('total_failed')} fallidos")
            else:
                logger.warning(f"⚠️  No se pudieron configurar webhooks automáticamente: {result.get('message')}")
                
        except Exception as e:
            logger.warning(f"⚠️  Error configurando webhooks automáticamente: {e}")
    
    def map_adminet_estado_to_tiendanube(self, estado: str, anulado: str) -> Dict[str, str]:
        """
        Mapear estado de AdministraNET a estados de TiendaNube.
        
        Args:
            estado: Estado del pedido en AdministraNET
            anulado: Campo anulado ("Si" o "No")
            
        Returns:
            Dict con order_status y fulfillment_status para TiendaNube
        """
        # Si está anulado, siempre es cancelled
        if anulado == "Si":
            return {
                'order_status': 'cancelled',
                'fulfillment_status': None
            }
        
        # Mapeo según estado
        estado_map = {
            'Pendiente': {'order_status': 'open', 'fulfillment_status': 'pending'},
            'En preparación': {'order_status': 'open', 'fulfillment_status': 'pending'},
            'Preparado': {'order_status': 'open', 'fulfillment_status': 'pending'},
            'En Remito': {'order_status': 'open', 'fulfillment_status': 'in_transit'},
            'Parcial': {'order_status': 'open', 'fulfillment_status': 'in_transit'},
            'Facturado': {'order_status': 'closed', 'fulfillment_status': 'delivered'},
            'Cerrado': {'order_status': 'closed', 'fulfillment_status': 'delivered'},
        }
        
        return estado_map.get(estado, {'order_status': 'open', 'fulfillment_status': 'pending'})

    def _should_skip_recent_sync(self, mapping: CustomerMapping) -> bool:
        """Evita loops: omitir si se sincronizó hace menos de SYNC_SKIP_MINUTES."""
        if not mapping.last_synced:
            return False
        cutoff = timezone.now() - timedelta(minutes=SYNC_SKIP_MINUTES)
        return mapping.last_synced >= cutoff

    @staticmethod
    def _build_adminet_data_from_tiendanube_customer(customer: Dict[str, Any]) -> Dict[str, Any]:
        from .customer_lookup import tiendanube_customer_to_form_fields

        tn_id = to_int_or_none(customer.get('id'))
        tn_fields = tiendanube_customer_to_form_fields(customer)
        name = tn_fields.get('tiendanube_name') or '-'
        if name == '-' and tn_fields.get('tiendanube_first_name'):
            name = (
                f"{tn_fields['tiendanube_first_name']} "
                f"{tn_fields.get('tiendanube_last_name', '')}"
            ).strip()
        addr = str_or_default(tn_fields.get('tiendanube_address'), '-')
        data = {
            'nombre_cliente': name,
            'Email': str_or_default(tn_fields.get('tiendanube_email') or customer.get('email'), '-'),
            'telefono': str_or_default(tn_fields.get('tiendanube_phone') or customer.get('phone'), '-'),
            'Calle': addr,
            'CUIT': str_or_default(
                tn_fields.get('tiendanube_document')
                or customer.get('identification')
                or customer.get('document'),
                '-',
            ),
            'Estado': 'Activo',
            'cliente_ecommerce': 'Si',
            'ListaPrecio': 'Lista 1',
        }
        if tn_id is not None:
            data['id_tiendanube'] = tn_id
        return data

    def _check_sync_enabled(self) -> Optional[Dict[str, Any]]:
        reason = tiendanube_sync_disabled_reason(self.tiendanube_config)
        if reason:
            return {'success': False, 'message': reason}
        return None

    @staticmethod
    def _is_adminet_ecommerce_customer(customer: Dict[str, Any]) -> bool:
        return str_or_default(customer.get('cliente_ecommerce'), 'No').strip().lower() == 'si'

    @staticmethod
    def _customer_email_for_tiendanube(customer: Dict[str, Any]) -> str:
        email = str_or_default(customer.get('Email'), '').strip()
        if email and email != '-':
            return email
        codigo = customer.get('Codigo')
        return f'adminet_{codigo or 0}@noemail.local'

    @staticmethod
    def _customer_email_is_real_for_dedup(email: str) -> bool:
        """True si el email permite deduplicación (no es fallback @noemail.local)."""
        normalized = (email or '').strip().lower()
        return bool(normalized) and not normalized.endswith('@noemail.local')

    def _build_tiendanube_payload_from_adminet(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'name': str_or_default(customer.get('nombre_cliente'), '-'),
            'email': self._customer_email_for_tiendanube(customer),
            'document': str_or_default(customer.get('CUIT'), '-'),
            'phone': str_or_default(customer.get('telefono'), '-'),
            'address': f"{customer.get('Calle', '')} {customer.get('NroCalle', '')}".strip(),
        }

    def _resolve_customer_mapping(
        self,
        customer: Dict[str, Any],
        tiendanube_id: Optional[int] = None,
    ) -> CustomerMapping:
        codigo = to_int_or_none(customer.get('Codigo'))
        mapping = None
        if codigo is not None:
            mapping = CustomerMapping.objects.filter(adminet_codigo=codigo).first()
        if mapping is None and tiendanube_id is not None:
            mapping = CustomerMapping.objects.filter(tiendanube_id=tiendanube_id).first()

        email = self._customer_email_for_tiendanube(customer)
        adminet_nombre = str_or_default(customer.get('nombre_cliente'), '')
        defaults = {
            'adminet_nombre': adminet_nombre,
            'adminet_email': email,
            'adminet_cliente_ecommerce': str_or_default(customer.get('cliente_ecommerce'), ''),
            'sync_status': CustomerMapping.SyncStatus.PENDING,
        }
        defaults.update(nombre_completo_a_campos_tiendanube(adminet_nombre))

        if mapping is None:
            return CustomerMapping.objects.create(
                adminet_codigo=codigo,
                tiendanube_id=tiendanube_id,
                tiendanube_email=email,
                **defaults,
            )

        update_fields = []
        if codigo is not None and mapping.adminet_codigo != codigo:
            mapping.adminet_codigo = codigo
            update_fields.append('adminet_codigo')
        if tiendanube_id is not None and mapping.tiendanube_id != tiendanube_id:
            mapping.tiendanube_id = tiendanube_id
            update_fields.append('tiendanube_id')
        for field, value in defaults.items():
            if field.startswith('tiendanube_') and field != 'tiendanube_email':
                if value and not getattr(mapping, field):
                    setattr(mapping, field, value)
                    update_fields.append(field)
                continue
            if getattr(mapping, field) != value and value:
                setattr(mapping, field, value)
                update_fields.append(field)
        if update_fields:
            mapping.save(update_fields=list(set(update_fields)))
        return mapping

    def _push_adminet_customer_to_tiendanube(
        self,
        customer: Dict[str, Any],
        mapping: Optional[CustomerMapping] = None,
    ) -> Tuple[bool, str, Optional[int], Optional[CustomerMapping]]:
        """
        Crear o actualizar un cliente AdministraNET en Tienda Nube.
        Persiste id_tiendanube en MySQL cuando se crea en TN.
        """
        if not self._is_adminet_ecommerce_customer(customer):
            return (
                False,
                'Cliente sin cliente_ecommerce=Si; no se publica en Tienda Nube',
                None,
                mapping,
            )

        tiendanube_id = to_int_or_none(customer.get('id_tiendanube'))
        if mapping and not tiendanube_id:
            tiendanube_id = to_int_or_none(mapping.tiendanube_id)

        tiendanube_data = self._build_tiendanube_payload_from_adminet(customer)
        codigo = to_int_or_none(customer.get('Codigo'))
        created_in_tn = False

        if tiendanube_id:
            result = self.tiendanube_service.update_customer(tiendanube_id, tiendanube_data)
        else:
            email = self._customer_email_for_tiendanube(customer)
            if self._customer_email_is_real_for_dedup(email):
                find_result = self.tiendanube_service.find_customer_by_email(email)
                if not find_result.get('success'):
                    return (
                        False,
                        find_result.get('message', 'Error buscando cliente por email'),
                        None,
                        mapping,
                    )
                existing = find_result.get('customer')
                if existing:
                    tiendanube_id = to_int_or_none(existing.get('id'))
                    if tiendanube_id and codigo is not None:
                        update_result = self.adminet_service.update_customer_tiendanube_id(
                            codigo, tiendanube_id
                        )
                        if not update_result.get('success'):
                            logger.warning(
                                'Error actualizando id_tiendanube en AdministraNET para cliente %s: %s',
                                codigo,
                                update_result.get('message'),
                            )
                        customer['id_tiendanube'] = tiendanube_id

            if tiendanube_id:
                result = self.tiendanube_service.update_customer(tiendanube_id, tiendanube_data)
            else:
                result = self.tiendanube_service.create_customer(tiendanube_data)
                created_in_tn = True
                if result.get('success'):
                    tn_customer = result.get('customer') or {}
                    tiendanube_id = to_int_or_none(tn_customer.get('id'))
                    if tiendanube_id and codigo is not None:
                        update_result = self.adminet_service.update_customer_tiendanube_id(
                            codigo, tiendanube_id
                        )
                        if not update_result.get('success'):
                            logger.warning(
                                'Error actualizando id_tiendanube en AdministraNET para cliente %s: %s',
                                codigo,
                                update_result.get('message'),
                            )
                        customer['id_tiendanube'] = tiendanube_id

        if not result.get('success'):
            return False, result.get('message', 'Error desconocido'), tiendanube_id, mapping

        try:
            mapping = mapping or self._resolve_customer_mapping(customer, tiendanube_id)
        except Exception as exc:
            logger.error('Error resolviendo CustomerMapping para cliente %s: %s', codigo, exc)
            return (
                False,
                f'Cliente sincronizado en Tienda Nube pero falló el mapeo local: {exc}',
                tiendanube_id,
                mapping,
            )

        mapping.tiendanube_id = tiendanube_id
        actualizar_snapshot_cliente_adminet(mapping, customer)
        mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
        mapping.last_synced = timezone.now()
        mapping.error_message = ''
        mapping.save()
        action = 'creado' if created_in_tn else 'actualizado'
        return True, f'Cliente {action} en Tienda Nube (ID: {tiendanube_id})', tiendanube_id, mapping

    def sync_customer_to_adminet(
        self, mapping: CustomerMapping, force: bool = False
    ) -> Tuple[bool, str]:
        """Sincronizar un cliente Tienda Nube → AdministraNET."""
        if not mapping.tiendanube_id:
            return False, 'El mapeo no tiene tiendanube_id'
        if not mapping.sync_enabled and not force:
            return False, 'Sincronización deshabilitada para este mapeo'
        tn_result = self.tiendanube_service.get_customer(mapping.tiendanube_id)
        if not tn_result.get('success'):
            msg = tn_result.get('message', 'Error obteniendo cliente de Tienda Nube')
            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
            mapping.error_message = msg
            mapping.save(update_fields=['sync_status', 'error_message'])
            return False, msg

        tn_customer = tn_result['customer']
        if not force and mapping.sync_status == CustomerMapping.SyncStatus.SYNCED:
            if not cliente_tn_modificado(tn_customer, mapping):
                return True, 'Omitido: sin cambios en Tienda Nube'

        adminet_data = self._build_adminet_data_from_tiendanube_customer(tn_customer)
        if not mapping.adminet_codigo and mapping.tiendanube_id:
            linked = self.adminet_service.get_customer_by_tiendanube_id(
                int(mapping.tiendanube_id)
            )
            if linked.get('success'):
                mapping.adminet_codigo = linked['customer'].get('Codigo')

        if mapping.adminet_codigo:
            result = self.adminet_service.update_customer(mapping.adminet_codigo, adminet_data)
        else:
            result = self.adminet_service.create_customer(adminet_data)
            if result.get('success'):
                mapping.adminet_codigo = result.get('customer_id')

        if result.get('success'):
            actualizar_snapshot_cliente_tiendanube(mapping, tn_customer)
            mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
            mapping.last_synced = timezone.now()
            mapping.error_message = ''
            mapping.save()
            return True, result.get('message', 'Cliente sincronizado hacia AdministraNET')

        mapping.sync_status = CustomerMapping.SyncStatus.ERROR
        mapping.error_message = result.get('message', 'Error desconocido')
        mapping.save(update_fields=['sync_status', 'error_message'])
        return False, mapping.error_message

    def sync_customer_to_tiendanube(
        self, mapping: CustomerMapping, force: bool = False
    ) -> Tuple[bool, str]:
        """Sincronizar un cliente AdministraNET → Tienda Nube (crear o actualizar)."""
        if not mapping.adminet_codigo:
            return False, 'El mapeo no tiene adminet_codigo'
        if not mapping.sync_enabled and not force:
            return False, 'Sincronización deshabilitada para este mapeo'
        an_result = self.adminet_service.get_customer(mapping.adminet_codigo)
        if not an_result.get('success'):
            msg = an_result.get('message', 'Cliente no encontrado en AdministraNET')
            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
            mapping.error_message = msg
            mapping.save(update_fields=['sync_status', 'error_message'])
            return False, msg

        customer = an_result['customer']
        if not force and mapping.sync_status == CustomerMapping.SyncStatus.SYNCED:
            if not cliente_adminet_cambio(mapping, customer):
                return True, 'Omitido: sin cambios en AdministraNET'

        ok, msg, _, _ = self._push_adminet_customer_to_tiendanube(customer, mapping=mapping)
        if not ok:
            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
            mapping.error_message = msg
            mapping.save(update_fields=['sync_status', 'error_message'])
        return ok, msg

    def sync_customers_from_tiendanube(
        self, sync_log: Optional[SyncLog] = None
    ) -> Dict[str, Any]:
        """Sincronizar clientes desde TiendaNube hacia AdministraNET."""
        disabled = self._check_sync_enabled()
        if disabled:
            return disabled
        try:
            if sync_log is None:
                sync_log = SyncLog.objects.create(
                    sync_type=SyncLog.SyncType.CUSTOMER,
                    direction=SyncLog.SyncDirection.TO_ADMINET,
                    status=SyncLog.Status.IN_PROGRESS,
                    tiendanube_config=self.tiendanube_config,
                    adminet_config=self.adminet_config
                )
            
            # Obtener clientes de TiendaNube
            tiendanube_result = self.tiendanube_service.get_customers(limit=100)
            if not tiendanube_result['success']:
                sync_log.complete_sync(False, tiendanube_result['message'])
                return tiendanube_result
            
            customers = tiendanube_result['customers']
            sync_log.total_items = len(customers)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for customer in customers:
                try:
                    tn_fields = tiendanube_customer_to_form_fields(customer)
                    create_defaults = {
                        k: v
                        for k, v in tn_fields.items()
                        if k != 'tiendanube_id' and v not in (None, '')
                    }
                    create_defaults['sync_status'] = CustomerMapping.SyncStatus.PENDING
                    mapping, created = CustomerMapping.objects.get_or_create(
                        tiendanube_id=customer['id'],
                        defaults=create_defaults,
                    )
                    if not created:
                        fill_fields = []
                        for field, value in create_defaults.items():
                            if field == 'sync_status' or not value:
                                continue
                            if not getattr(mapping, field):
                                setattr(mapping, field, value)
                                fill_fields.append(field)
                        if fill_fields:
                            mapping.save(update_fields=fill_fields)
                    
                    if created or mapping.sync_status != CustomerMapping.SyncStatus.SYNCED:
                        ok, msg = self.sync_customer_to_adminet(mapping, force=True)
                        if ok and 'Omitido' not in msg:
                            successful_syncs += 1
                        elif not ok:
                            failed_syncs += 1
                    elif cliente_tn_modificado(customer, mapping):
                        ok, msg = self.sync_customer_to_adminet(mapping, force=False)
                        if ok and 'Omitido' not in msg:
                            successful_syncs += 1
                        elif not ok:
                            failed_syncs += 1

                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing customer {customer.get('id')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            self._complete_sync_with_status(sync_log, successful_syncs, failed_syncs, len(customers))
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(customers),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_customers_from_tiendanube: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }

    def sync_customers_from_adminet(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        sync_log: Optional[SyncLog] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Sincronizar clientes desde AdministraNET hacia Tiendanube.
        Solo clientes con cliente_ecommerce='Si': crea en TN si no tienen id_tiendanube
        o actualiza si ya están vinculados.

        Args:
            limit: Cantidad máxima de clientes a procesar en este lote (None = todos desde offset).
            offset: Desplazamiento sobre la lista completa obtenida de AdministraNET.
            sync_log: Log existente a reutilizar (p. ej. sync inicial por lotes).
        """
        disabled = self._check_sync_enabled()
        if disabled:
            return disabled
        try:
            if sync_log is None:
                sync_log = SyncLog.objects.create(
                    sync_type=SyncLog.SyncType.CUSTOMER,
                    direction=SyncLog.SyncDirection.FROM_ADMINET,
                    status=SyncLog.Status.IN_PROGRESS,
                    tiendanube_config=self.tiendanube_config,
                    adminet_config=self.adminet_config
                )

            adminet_result = self.adminet_service.get_customers(
                limit=None,
                cliente_ecommerce='Si',
            )
            if not adminet_result['success']:
                sync_log.complete_sync(False, adminet_result['message'])
                return adminet_result

            all_customers = adminet_result['data']
            total_available = len(all_customers)
            if limit is not None:
                customers = all_customers[offset:offset + limit]
            else:
                customers = all_customers[offset:]

            if not customers and total_available == 0:
                message = (
                    'No hay clientes con cliente_ecommerce=Si para sincronizar. '
                    'Marque clientes en AdministraNET como ecommerce antes de publicarlos en Tienda Nube.'
                )
                logger.warning(message)
                sync_log.status = SyncLog.Status.COMPLETED
                sync_log.total_items = 0
                sync_log.processed_items = 0
                sync_log.successful_items = 0
                sync_log.failed_items = 0
                sync_log.completed_at = timezone.now()
                sync_log.error_message = message
                sync_log.save()
                return {
                    'success': True,
                    'message': message,
                    'sync_log_id': sync_log.id,
                    'total_processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0,
                    'total_available': 0,
                    'offset': offset,
                    'limit': limit,
                    'has_more': False,
                }

            if not customers:
                sync_log.status = SyncLog.Status.COMPLETED
                sync_log.total_items = 0
                sync_log.processed_items = 0
                sync_log.successful_items = 0
                sync_log.failed_items = 0
                sync_log.completed_at = timezone.now()
                sync_log.save()
                return {
                    'success': True,
                    'message': 'No hay más clientes en este lote.',
                    'sync_log_id': sync_log.id,
                    'total_processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0,
                    'total_available': total_available,
                    'offset': offset,
                    'limit': limit,
                    'has_more': offset < total_available,
                }

            sync_log.total_items = len(customers)
            sync_log.save()

            successful_syncs = 0
            failed_syncs = 0
            skipped = 0

            for customer in customers:
                try:
                    codigo = to_int_or_none(customer.get('Codigo'))
                    mapping_existente = None
                    if codigo is not None:
                        mapping_existente = CustomerMapping.objects.filter(
                            adminet_codigo=codigo
                        ).first()
                    if (
                        not force
                        and mapping_existente
                        and mapping_existente.sync_status == CustomerMapping.SyncStatus.SYNCED
                        and not cliente_adminet_cambio(mapping_existente, customer)
                    ):
                        skipped += 1
                        sync_log.processed_items += 1
                        sync_log.save(update_fields=['processed_items'])
                        continue

                    ok, msg, _, mapping = self._push_adminet_customer_to_tiendanube(customer)
                    if ok:
                        successful_syncs += 1
                        logger.debug(
                            'Cliente %s sincronizado hacia Tienda Nube: %s',
                            customer.get('Codigo'),
                            msg,
                        )
                    else:
                        failed_syncs += 1
                        if mapping:
                            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                            mapping.error_message = msg
                            mapping.save(update_fields=['sync_status', 'error_message'])
                        logger.error(
                            'Error sincronizando cliente %s hacia Tienda Nube: %s',
                            customer.get('Codigo'),
                            msg,
                        )

                    sync_log.processed_items += 1
                    sync_log.successful_items = successful_syncs
                    sync_log.failed_items = failed_syncs
                    sync_log.save(
                        update_fields=['processed_items', 'successful_items', 'failed_items']
                    )

                except Exception as e:
                    logger.error(f"Error syncing customer {customer.get('Codigo')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.successful_items = successful_syncs
                    sync_log.failed_items = failed_syncs
                    sync_log.save(
                        update_fields=['processed_items', 'successful_items', 'failed_items']
                    )

            self._complete_sync_with_status(sync_log, successful_syncs, failed_syncs, len(customers))

            next_offset = offset + len(customers)
            return {
                'success': True,
                'message': (
                    f'Sincronización completada: {successful_syncs} clientes en Tienda Nube, '
                    f'{failed_syncs} fallidas, {skipped} omitidos (cliente_ecommerce=Si)'
                ),
                'sync_log_id': sync_log.id,
                'total_processed': len(customers),
                'successful': successful_syncs,
                'failed': failed_syncs,
                'skipped': skipped,
                'total_available': total_available,
                'offset': offset,
                'limit': limit,
                'has_more': next_offset < total_available,
            }

        except Exception as e:
            logger.error(f"Error in sync_customers_from_adminet: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }

    # ============================================================================
    # PRODUCTOS
    # ============================================================================

    def sync_products_from_tiendanube(
        self, sync_log: Optional[SyncLog] = None
    ) -> Dict[str, Any]:
        """Sincronizar productos desde Tiendanube hacia AdministraNET."""
        try:
            if sync_log is None:
                sync_log = SyncLog.objects.create(
                    sync_type=SyncLog.SyncType.PRODUCT,
                    direction=SyncLog.SyncDirection.TO_ADMINET,
                    status=SyncLog.Status.IN_PROGRESS,
                    tiendanube_config=self.tiendanube_config,
                    adminet_config=self.adminet_config
                )
            
            # Obtener productos de Tiendanube
            tiendanube_result = self.product_service.get_products(limit=None)  # Sin límite - sincronizar todos
            if not tiendanube_result['success']:
                sync_log.complete_sync(False, tiendanube_result['message'])
                return tiendanube_result
            
            products = tiendanube_result['products']
            sync_log.total_items = len(products)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for product in products:
                try:
                    # Verificar si ya existe el mapeo
                    mapping, created = ProductMapping.objects.get_or_create(
                        tiendanube_id=product['id'],
                        defaults={
                            'tiendanube_name': product.get('name', ''),
                            'tiendanube_sku': product.get('sku', ''),
                            'tiendanube_price': product.get('price', 0),
                            'tiendanube_stock': product.get('stock', 0),
                            'sync_status': ProductMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or mapping.sync_status != ProductMapping.SyncStatus.SYNCED:
                        # Mapear datos de Tiendanube a AdministraNET
                        adminet_data = self.mapping_service.map_tiendanube_to_adminet_product(product)
                        
                        if mapping.adminet_id:
                            # Actualizar producto existente
                            result = self.adminet_service.update_product(mapping.adminet_id, adminet_data)
                        else:
                            # Crear nuevo producto
                            result = self.adminet_service.create_product(adminet_data)
                            if result['success']:
                                mapping.adminet_id = result.get('product_id')
                        
                        if result['success']:
                            # Actualizar mapeo con datos de Tiendanube
                            self.mapping_service.update_product_mapping_from_tiendanube(mapping, product)
                            mapping.sync_status = ProductMapping.SyncStatus.SYNCED
                            mapping.last_synced = timezone.now()
                            mapping.save()
                            successful_syncs += 1
                        else:
                            mapping.sync_status = ProductMapping.SyncStatus.ERROR
                            mapping.error_message = result['message']
                            mapping.save()
                            failed_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing product {product.get('id')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar sincronización
            self._complete_sync_with_status(sync_log, successful_syncs, failed_syncs, len(products))
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(products),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_products_from_tiendanube: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }

    def sync_products_from_adminet(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        sync_log: Optional[SyncLog] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Sincronizar productos desde AdministraNET hacia Tiendanube.

        Args:
            limit: Cantidad máxima de productos a procesar en este lote (None = todos desde offset).
            offset: Desplazamiento sobre la lista completa obtenida de AdministraNET.
            sync_log: Log existente a reutilizar (p. ej. sync inicial por lotes).
        """
        try:
            if sync_log is None:
                sync_log = SyncLog.objects.create(
                    sync_type=SyncLog.SyncType.PRODUCT,
                    direction=SyncLog.SyncDirection.FROM_ADMINET,
                    status=SyncLog.Status.IN_PROGRESS,
                    tiendanube_config=self.tiendanube_config,
                    adminet_config=self.adminet_config
                )
            
            deposito_id = self.adminet_config.deposito_tiendanube_id
            if not deposito_id:
                msg = (
                    'Configure deposito_tiendanube_id en la integración AdministraNET. '
                    'Tiendanube publica stock por artículo en unidades del depósito definido.'
                )
                sync_log.complete_sync(False, msg)
                return {'success': False, 'message': msg}

            logger.info('Sincronizando productos desde depósito %s', deposito_id)
            adminet_result = self.adminet_service.get_products_with_stock_by_deposito(
                deposito_id=deposito_id,
                limit=None,
                ecommerce='Si',
                disponible_vta='Si',
            )
            
            if not adminet_result['success']:
                sync_log.complete_sync(False, adminet_result['message'])
                return adminet_result
            
            all_products = adminet_result['results']
            total_available = len(all_products)
            if limit is not None:
                products = all_products[offset:offset + limit]
            else:
                products = all_products[offset:]

            if not products:
                sync_log.status = SyncLog.Status.COMPLETED
                sync_log.total_items = 0
                sync_log.processed_items = 0
                sync_log.successful_items = 0
                sync_log.failed_items = 0
                sync_log.completed_at = timezone.now()
                sync_log.save()
                return {
                    'success': True,
                    'message': 'No hay más productos en este lote.',
                    'sync_log_id': sync_log.id,
                    'total_processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'total_available': total_available,
                    'offset': offset,
                    'limit': limit,
                    'has_more': offset < total_available,
                }

            sync_log.total_items = len(products)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            skipped = 0
            stock_price_pending: List[dict] = []

            for adminet_product in products:
                try:
                    mapping, created = ProductMapping.objects.get_or_create(
                        adminet_id=adminet_product['IDArt'],
                        defaults={
                            'adminet_nombre': adminet_product.get('NombreArticulo', ''),
                            'adminet_codigo_articulo': adminet_product.get('CodigoArticuloT', ''),
                            'sync_status': ProductMapping.SyncStatus.PENDING
                        }
                    )

                    necesita_sync, _motivo = producto_requiere_sync_adminet_a_tn(
                        mapping,
                        adminet_product,
                        deposito_id,
                        force=force or created,
                        config=self.adminet_config,
                    )
                    if not necesita_sync:
                        skipped += 1
                        sync_log.processed_items += 1
                        sync_log.save(update_fields=['processed_items'])
                        continue

                    self.mapping_service.update_product_mapping_from_adminet(
                        mapping, adminet_product, deposito_id=deposito_id
                    )
                    tiendanube_data = self.mapping_service.map_adminet_to_tiendanube_product(
                        adminet_product,
                        deposito_id=deposito_id
                    )

                    if mapping.tiendanube_id:
                        variant_mapping = self._get_product_variant_mapping(mapping)
                        if variant_mapping and variant_mapping.tiendanube_variant_id:
                            queued = self._queue_stock_price_update(
                                stock_price_pending,
                                mapping,
                                adminet_product,
                                tiendanube_data,
                                variant_mapping.tiendanube_variant_id,
                            )
                            if queued:
                                if len(stock_price_pending) >= STOCK_PRICE_BATCH_MAX:
                                    ok, fail = self._flush_stock_price_batch(
                                        stock_price_pending
                                    )
                                    successful_syncs += ok
                                    failed_syncs += fail
                            else:
                                self._finalize_product_sync_error(
                                    mapping,
                                    'Sin datos de variante para actualizar',
                                )
                                failed_syncs += 1
                        else:
                            result = self._sync_product_update_fallback(
                                mapping, tiendanube_data
                            )
                            if result.get('success'):
                                self._finalize_product_sync_success(
                                    mapping, adminet_product
                                )
                                successful_syncs += 1
                            else:
                                self._finalize_product_sync_error(
                                    mapping, result.get('message', '')
                                )
                                failed_syncs += 1
                    else:
                        result = self._sync_product_create(
                            mapping, tiendanube_data, adminet_product
                        )
                        if result.get('success'):
                            successful_syncs += 1
                        else:
                            failed_syncs += 1

                    sync_log.processed_items += 1
                    sync_log.successful_items = successful_syncs
                    sync_log.failed_items = failed_syncs
                    sync_log.save(
                        update_fields=['processed_items', 'successful_items', 'failed_items']
                    )

                except Exception as e:
                    logger.error(
                        f"Error syncing product {adminet_product.get('IDArt')}: {e}"
                    )
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.successful_items = successful_syncs
                    sync_log.failed_items = failed_syncs
                    sync_log.save(
                        update_fields=['processed_items', 'successful_items', 'failed_items']
                    )

            if stock_price_pending:
                ok, fail = self._flush_stock_price_batch(stock_price_pending)
                successful_syncs += ok
                failed_syncs += fail

            # Completar sincronización
            self._complete_sync_with_status(sync_log, successful_syncs, failed_syncs, len(products))
            
            next_offset = offset + len(products)
            return {
                'success': True,
                'message': (
                    f'Sincronización completada: {successful_syncs} exitosas, '
                    f'{failed_syncs} fallidas, {skipped} omitidas'
                ),
                'sync_log_id': sync_log.id,
                'total_processed': len(products),
                'successful': successful_syncs,
                'failed': failed_syncs,
                'skipped': skipped,
                'total_available': total_available,
                'offset': offset,
                'limit': limit,
                'has_more': next_offset < total_available,
            }
            
        except Exception as e:
            logger.error(f"Error in sync_products_from_adminet: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }

    def _strip_images_from_product_payload(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Omitir imágenes en POST /products (creación inicial)."""
        payload = dict(product_data)
        payload.pop('images', None)
        return payload

    def _get_product_variant_mapping(
        self, mapping: ProductMapping
    ) -> Optional[ProductVariantMapping]:
        return mapping.variants.filter(tiendanube_variant_id__isnull=False).first()

    def _extract_variant_fields(
        self, tiendanube_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        variants = tiendanube_data.get('variants') or [{}]
        source = variants[0] if variants else {}
        return {
            'sku': source.get('sku'),
            'price': source.get('price'),
            'stock': source.get('stock'),
            'stock_management': True,
        }

    def _build_stock_price_patch_payload(
        self,
        pending_items: List[dict],
        location_id: Optional[int] = None,
    ) -> List[dict]:
        by_product: Dict[int, dict] = {}
        for item in pending_items:
            product_id = item['product_id']
            variant_entry: Dict[str, Any] = {'id': item['variant_id']}
            if item.get('price') is not None:
                variant_entry['price'] = item['price']
            if item.get('stock') is not None:
                variant_entry['inventory_levels'] = [
                    build_inventory_level_entry(item['stock'], location_id)
                ]
            if product_id not in by_product:
                by_product[product_id] = {'id': product_id, 'variants': []}
            by_product[product_id]['variants'].append(variant_entry)
        return list(by_product.values())

    def _resolve_tiendanube_location_id(self) -> Optional[int]:
        config = getattr(self, 'tiendanube_config', None)
        if config is None:
            return None
        return to_int_or_none(getattr(config, 'location_id', None))

    def _queue_stock_price_update(
        self,
        pending: List[dict],
        mapping: ProductMapping,
        adminet_product: dict,
        tiendanube_data: Dict[str, Any],
        variant_id: int,
    ) -> bool:
        variant_fields = self._extract_variant_fields(tiendanube_data)
        if variant_fields.get('price') is None and variant_fields.get('stock') is None:
            return False
        pending.append({
            'product_id': mapping.tiendanube_id,
            'variant_id': variant_id,
            'price': variant_fields.get('price'),
            'stock': variant_fields.get('stock'),
            'mapping': mapping,
            'adminet_product': adminet_product,
        })
        return True

    def _flush_stock_price_batch(self, pending: List[dict]) -> Tuple[int, int]:
        if not pending:
            return 0, 0
        batch = pending[:]
        pending.clear()
        payload = self._build_stock_price_patch_payload(
            batch,
            location_id=self._resolve_tiendanube_location_id(),
        )
        result = self.product_service.patch_products_stock_price(payload)
        ok_count = 0
        fail_count = 0
        if result.get('success'):
            for item in batch:
                self._finalize_product_sync_success(
                    item['mapping'], item['adminet_product']
                )
                ok_count += 1
        else:
            msg = result.get('message', 'Error en batch stock/precio')
            for item in batch:
                self._finalize_product_sync_error(item['mapping'], msg)
                fail_count += 1
        return ok_count, fail_count

    def _sync_product_create(
        self,
        mapping: ProductMapping,
        tiendanube_data: Dict[str, Any],
        adminet_product: dict,
    ) -> Dict[str, Any]:
        create_payload = normalize_product_visibility_payload(
            self._strip_images_from_product_payload(tiendanube_data)
        )
        result = self.product_service.create_product(create_payload)
        if result.get('success'):
            tn_product = result.get('product', {})
            mapping.tiendanube_id = tn_product.get('id')
            self._save_variant_mapping_from_tn_product(
                mapping, tn_product, adminet_product
            )
            self._finalize_product_sync_success(mapping, adminet_product)
        else:
            self._finalize_product_sync_error(
                mapping, result.get('message', 'Error creando producto')
            )
        return result

    def _sync_product_update_fallback(
        self, mapping: ProductMapping, tiendanube_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """GET /products + PUT variant cuando no hay tiendanube_variant_id en mapping."""
        existing_product = self.product_service.get_product(mapping.tiendanube_id)
        if not existing_product.get('success'):
            return existing_product

        product_data = existing_product['product']
        variants = product_data.get('variants', [])
        variant_fields = self._extract_variant_fields(tiendanube_data)

        if variants:
            variant_id = variants[0].get('id')
            result = self.product_service.update_variant(
                mapping.tiendanube_id,
                variant_id,
                variant_fields,
            )
            if result.get('success'):
                self._save_variant_mapping_from_tn_product(
                    mapping,
                    {
                        'id': mapping.tiendanube_id,
                        'variants': [result.get('variant', {})],
                    },
                    {},
                )
        else:
            result = self.product_service.create_variant(
                mapping.tiendanube_id,
                tiendanube_data.get('variants', [{}])[0],
            )
            if result.get('success'):
                variant = result.get('variant', {})
                ProductVariantMapping.objects.update_or_create(
                    product_mapping=mapping,
                    defaults={
                        'tiendanube_variant_id': variant.get('id'),
                        'tiendanube_sku': variant.get('sku', ''),
                    },
                )
        return result

    def _save_variant_mapping_from_tn_product(
        self,
        mapping: ProductMapping,
        tn_product: dict,
        adminet_product: dict,
    ) -> None:
        variants = tn_product.get('variants') or []
        if not variants:
            return
        variant = variants[0]
        defaults = {
            'tiendanube_variant_id': variant.get('id'),
            'tiendanube_sku': variant.get('sku', ''),
            'tiendanube_price': variant.get('price'),
            'tiendanube_stock': variant.get('stock', 0),
            'tiendanube_product_id': tn_product.get('id'),
        }
        if adminet_product:
            defaults['adminet_id'] = adminet_product.get('IDArt')
            defaults['adminet_nombre'] = adminet_product.get('NombreArticulo', '')
        ProductVariantMapping.objects.update_or_create(
            product_mapping=mapping,
            defaults=defaults,
        )

    def _finalize_product_sync_success(
        self, mapping: ProductMapping, adminet_product: dict
    ) -> None:
        if adminet_product:
            deposito_id = self.adminet_config.deposito_tiendanube_id
            self.mapping_service.update_product_mapping_from_adminet(
                mapping,
                adminet_product,
                deposito_id=deposito_id,
            )
            precios = precios_tiendanube_desde_articulo(
                adminet_product,
                config=self.adminet_config,
            )
            mapping.tiendanube_price = precios['price']
            mapping.tiendanube_cost = precios['cost']
            if mapping.adminet_stock is not None:
                mapping.tiendanube_stock = int(mapping.adminet_stock)
            nombre = adminet_product.get('NombreArticulo')
            if nombre:
                mapping.tiendanube_name = str(nombre)[:255]
            sku = adminet_product.get('NroCodBarra')
            if sku:
                mapping.tiendanube_sku = str(sku)
        if mapping.tiendanube_id and adminet_product.get('IDArt'):
            update_result = self.adminet_service.update_product_tiendanube_id(
                adminet_product['IDArt'],
                mapping.tiendanube_id,
            )
            if not update_result.get('success'):
                logger.warning(
                    "Error actualizando id_tiendanube en AdministraNET: "
                    f"{update_result.get('message')}"
                )
        mapping.sync_status = ProductMapping.SyncStatus.SYNCED
        mapping.last_synced = timezone.now()
        mapping.error_message = ''
        mapping.save()

    def _finalize_product_sync_error(
        self, mapping: ProductMapping, message: str
    ) -> None:
        mapping.sync_status = ProductMapping.SyncStatus.ERROR
        mapping.error_message = message
        mapping.save()

    def sync_product_variants_from_tiendanube(self, product_mapping: ProductMapping) -> Dict[str, Any]:
        """Sincronizar variantes de un producto desde Tiendanube hacia AdministraNET."""
        try:
            if not product_mapping.tiendanube_id:
                return {
                    'success': False,
                    'message': 'El producto no tiene ID de Tiendanube'
                }
            
            # Obtener variantes de Tiendanube
            variants_result = self.product_service.get_product_variants(product_mapping.tiendanube_id)
            if not variants_result['success']:
                return variants_result
            
            variants = variants_result['variants']
            successful_syncs = 0
            failed_syncs = 0
            
            for variant in variants:
                try:
                    # Verificar si ya existe el mapeo de variante
                    variant_mapping, created = ProductVariantMapping.objects.get_or_create(
                        tiendanube_variant_id=variant['id'],
                        product_mapping=product_mapping,
                        defaults={
                            'tiendanube_name': variant.get('name', ''),
                            'tiendanube_sku': variant.get('sku', ''),
                            'tiendanube_price': variant.get('price', 0),
                            'tiendanube_stock': variant.get('stock', 0),
                            'sync_status': ProductVariantMapping.SyncStatus.PENDING
                        }
                    )
                    
                    if created or variant_mapping.sync_status != ProductVariantMapping.SyncStatus.SYNCED:
                        # Mapear datos de variante de Tiendanube a AdministraNET
                        adminet_data = self.mapping_service.map_tiendanube_to_adminet_variant(variant)
                        
                        if variant_mapping.adminet_id:
                            # Actualizar variante existente
                            result = self.adminet_service.update_product(variant_mapping.adminet_id, adminet_data)
                        else:
                            # Crear nueva variante como producto separado
                            result = self.adminet_service.create_product(adminet_data)
                            if result['success']:
                                variant_mapping.adminet_id = result.get('product_id')
                        
                        if result['success']:
                            # Actualizar mapeo de variante
                            self._update_variant_mapping_from_tiendanube(variant_mapping, variant)
                            variant_mapping.sync_status = ProductVariantMapping.SyncStatus.SYNCED
                            variant_mapping.last_synced = timezone.now()
                            variant_mapping.save()
                            successful_syncs += 1
                        else:
                            variant_mapping.sync_status = ProductVariantMapping.SyncStatus.ERROR
                            variant_mapping.error_message = result['message']
                            variant_mapping.save()
                            failed_syncs += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing variant {variant.get('id')}: {e}")
                    failed_syncs += 1
            
            return {
                'success': True,
                'message': f'Sincronización de variantes completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'total_processed': len(variants),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_product_variants_from_tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error en sincronización de variantes: {str(e)}'
            }

    # ============================================================================
    # MÉTODOS DE MAPEO (DEPRECATED - USAR AutomaticMappingService)
    # ============================================================================
    
    # Los métodos de mapeo han sido movidos al AutomaticMappingService
    # para centralizar toda la lógica de mapeo y mantener el código organizado.

    # ============================================================================
    # ÓRDENES (mantener implementación existente)
    # ============================================================================

    def catch_up_missing_orders(self, since=None) -> Dict[str, Any]:
        """
        GET orders TN e importar pedidos pagados ausentes en AdministraNET.

        Usa handler canónico order/paid; no duplica OrderMapping existentes.
        """
        from .webhook_service import WebhookProcessor
        from ..models import WebhookConfig, WebhookEvent

        reference = since or self.tiendanube_config.last_sync
        orders_result = self.tiendanube_service.get_orders(limit=50)
        if not orders_result.get('success'):
            return orders_result

        orders = orders_result.get('orders') or []
        imported = 0
        skipped_existing = 0
        failed = 0

        webhook_config = WebhookConfig.objects.filter(
            tiendanube_config=self.tiendanube_config,
            is_active=True,
        ).first()
        if not webhook_config:
            return {
                'success': False,
                'message': 'Sin WebhookConfig activo para catch-up.',
            }

        for order in orders:
            tn_id = order.get('id')
            if not tn_id:
                continue

            existing = OrderMapping.objects.filter(tiendanube_id=tn_id).first()
            if existing and existing.adminet_codigo:
                skipped_existing += 1
                continue

            if order.get('payment_status') != 'paid':
                continue

            if reference is not None:
                updated_at_raw = order.get('updated_at') or order.get('created_at')
                if updated_at_raw:
                    try:
                        updated_at = timezone.datetime.fromisoformat(
                            str(updated_at_raw).replace('Z', '+00:00')
                        )
                        if timezone.is_naive(updated_at):
                            updated_at = timezone.make_aware(updated_at)
                        if updated_at < reference:
                            continue
                    except (TypeError, ValueError):
                        pass

            synthetic_event = WebhookEvent(
                webhook_config=webhook_config,
                event_type='order/paid',
                event_id=f'catchup-{tn_id}',
                resource_id=tn_id,
                resource_type='order',
                payload={'type': 'order/paid', 'id': tn_id, 'data': order},
                headers={},
            )
            result = WebhookProcessor._handle_order_event(
                synthetic_event,
                synthetic_event.payload,
            )
            if result.get('success'):
                imported += 1
            else:
                failed += 1

        self.tiendanube_config.last_sync = timezone.now()
        self.tiendanube_config.save(update_fields=['last_sync'])

        return {
            'success': failed == 0,
            'imported': imported,
            'skipped_existing': skipped_existing,
            'failed': failed,
            'total_fetched': len(orders),
        }
    
    def sync_orders_from_tiendanube(
        self, sync_log: Optional[SyncLog] = None
    ) -> Dict[str, Any]:
        """Sincronizar órdenes desde Tiendanube hacia AdministraNET."""
        try:
            if sync_log is None:
                sync_log = SyncLog.objects.create(
                    sync_type=SyncLog.SyncType.ORDER,
                    direction=SyncLog.SyncDirection.TO_ADMINET,
                    status=SyncLog.Status.IN_PROGRESS,
                    tiendanube_config=self.tiendanube_config,
                    adminet_config=self.adminet_config
                )
            
            # Obtener órdenes de Tiendanube
            tiendanube_result = self.tiendanube_service.get_orders(limit=50)
            if not tiendanube_result['success']:
                sync_log.complete_sync(False, tiendanube_result['message'])
                return tiendanube_result
            
            orders = tiendanube_result['orders']
            sync_log.total_items = len(orders)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            
            for order in orders:
                try:
                    # Verificar si ya existe el mapeo
                    mapping, created = OrderMapping.objects.get_or_create(
                        tiendanube_id=order['id'],
                        defaults={
                            'tiendanube_number': order.get('number', ''),
                            'tiendanube_total': order.get('total', 0),
                            'tiendanube_currency': order.get('currency', ''),
                            'tiendanube_status': order.get('status', ''),
                            'tiendanube_payment_status': order.get('payment_status', ''),
                            'tiendanube_customer_id': order.get('customer', {}).get('id'),
                            'tiendanube_customer_email': order.get('customer', {}).get('email', ''),
                            'tiendanube_customer_name': order.get('customer', {}).get('name', ''),
                            'tiendanube_shipping_address': order.get('shipping_address', {}),
                            'tiendanube_billing_address': order.get('billing_address', {}),
                            'tiendanube_payment_method': order.get('payment', {}).get('method', ''),
                            'tiendanube_shipping_method': order.get('shipping', {}).get('method', ''),
                            'tiendanube_created_at': order.get('created_at'),
                            'tiendanube_updated_at': order.get('updated_at'),
                            'sync_status': OrderMapping.SyncStatus.PENDING
                        }
                    )
                    
                    # Actualizar campos si el mapeo ya existía
                    if not created:
                        mapping.tiendanube_number = order.get('number', '')
                        mapping.tiendanube_total = order.get('total', 0)
                        mapping.tiendanube_currency = order.get('currency', '')
                        mapping.tiendanube_status = order.get('status', '')
                        mapping.tiendanube_payment_status = order.get('payment_status', '')
                        mapping.tiendanube_customer_id = order.get('customer', {}).get('id')
                        mapping.tiendanube_customer_email = order.get('customer', {}).get('email', '')
                        mapping.tiendanube_customer_name = order.get('customer', {}).get('name', '')
                        mapping.tiendanube_shipping_address = order.get('shipping_address', {})
                        mapping.tiendanube_billing_address = order.get('billing_address', {})
                        mapping.tiendanube_payment_method = order.get('payment', {}).get('method', '')
                        mapping.tiendanube_shipping_method = order.get('shipping', {}).get('method', '')
                        mapping.tiendanube_created_at = order.get('created_at')
                        mapping.tiendanube_updated_at = order.get('updated_at')
                        mapping.save()
                    
                    if created or mapping.sync_status != OrderMapping.SyncStatus.SYNCED:
                        # Verificar si la orden debe crearse en AdministraNET
                        if not mapping.adminet_codigo:
                            # Preparar datos de la orden para AdministraNET
                            order_data_for_adminet = {
                                'id': order.get('id'),
                                'number': order.get('number'),
                                'customer': order.get('customer', {}),
                                'shipping_address': order.get('shipping_address', {}),
                                'shipping': order.get('shipping', {}),
                                'payment': order.get('payment', {}),
                                'products': order.get('products', []),
                                'subtotal': order.get('subtotal', 0),
                                'total': order.get('total', 0),
                                'discount': order.get('discount', 0),
                                'shipping_cost': order.get('shipping_cost', 0),
                                'payment_status': order.get('payment_status', ''),
                                'created_at': order.get('created_at', ''),
                                'updated_at': order.get('updated_at', ''),
                                'adminet_customer_id': mapping.tiendanube_customer_id or 1
                            }
                            
                            # Mapear productos de TiendaNube a AdministraNET
                            for product in order_data_for_adminet['products']:
                                # Buscar mapeo del producto
                                product_mapping = ProductMapping.objects.filter(
                                    tiendanube_id=product.get('product_id')
                                ).first()
                                
                                if product_mapping and product_mapping.adminet_id:
                                    product['adminet_product_id'] = product_mapping.adminet_id
                                else:
                                    product['adminet_product_id'] = 0  # No mapeado
                                    logger.warning(f"Producto {product.get('product_id')} no está mapeado")
                            
                            # Crear orden en AdministraNET
                            result = self.adminet_service.create_order_from_tiendanube(
                                order_data_for_adminet,
                                deposito_id=self.adminet_config.deposito_tiendanube_id or 1,
                                user_id=1,  # Usuario del sistema
                                punto_venta_id=self.adminet_config.punto_venta_tiendanube_id or 1  # Punto de venta configurado
                            )
                            
                            if result['success']:
                                mapping.adminet_codigo = result['codigo_movimiento']
                                mapping.adminet_numero = result['nro_comprobante']
                                mapping.adminet_total = order.get('total', 0)
                                mapping.adminet_estado = 'Pendiente'  # Estado por defecto
                                mapping.sync_status = OrderMapping.SyncStatus.SYNCED
                                mapping.last_synced = timezone.now()
                                mapping.save()
                                successful_syncs += 1
                                logger.info(f"Orden {order.get('number')} creada en AdministraNET: {result['nro_comprobante']}")
                            else:
                                mapping.sync_status = OrderMapping.SyncStatus.ERROR
                                mapping.error_message = result['message']
                                mapping.save()
                                failed_syncs += 1
                                logger.error(f"Error creando orden {order.get('number')}: {result['message']}")
                        else:
                            # La orden ya existe en AdministraNET
                            mapping.sync_status = OrderMapping.SyncStatus.SYNCED
                            mapping.last_synced = timezone.now()
                            mapping.save()
                            successful_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error syncing order {order.get('id')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar sincronización
            self._complete_sync_with_status(sync_log, successful_syncs, failed_syncs, len(orders))
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful_syncs} exitosas, {failed_syncs} fallidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(orders),
                'successful': successful_syncs,
                'failed': failed_syncs
            }
            
        except Exception as e:
            logger.error(f"Error in sync_orders_from_tiendanube: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }
    
    def sync_order_status_to_tiendanube(self, hours: int = 24) -> Dict[str, Any]:
        """
        Sincronizar estados de órdenes desde AdministraNET hacia TiendaNube.
        
        Args:
            hours: Horas hacia atrás para buscar cambios (default: 24)
            
        Returns:
            Dict con el resultado de la sincronización
        """
        try:
            logger.info(f"Iniciando sincronización de estados de órdenes (últimas {hours} horas)")
            
            # Obtener pedidos de TiendaNube modificados recientemente
            result = self.adminet_service.get_tiendanube_orders_with_changes(hours=hours)
            
            if not result['success']:
                return result
            
            orders = result['orders']
            successful_updates = 0
            failed_updates = 0
            
            for order in orders:
                try:
                    tiendanube_id = order.get('id_tiendanube')
                    estado = order.get('Estado', '')
                    anulado = order.get('anulado', 'No')
                    
                    # Mapear estado de AdministraNET a TiendaNube
                    mapped_status = self.map_adminet_estado_to_tiendanube(estado, anulado)
                    
                    logger.info(f"Sincronizando orden {tiendanube_id}: {estado} → {mapped_status}")
                    
                    # Actualizar estado en TiendaNube
                    # Nota: TiendaNube API puede tener limitaciones en actualización de estados
                    # Por ahora, solo registramos el cambio
                    
                    # Actualizar OrderMapping si existe
                    order_mapping = OrderMapping.objects.filter(
                        tiendanube_id=tiendanube_id
                    ).first()
                    
                    if order_mapping:
                        order_mapping.adminet_estado = estado
                        order_mapping.tiendanube_status = mapped_status['order_status']
                        order_mapping.last_synced = timezone.now()
                        order_mapping.save()
                    
                    successful_updates += 1
                    
                except Exception as e:
                    logger.error(f"Error actualizando estado de orden {order.get('id_tiendanube')}: {e}")
                    failed_updates += 1
            
            return {
                'success': True,
                'message': f'Sincronización de estados completada: {successful_updates} exitosas, {failed_updates} fallidas',
                'total_processed': len(orders),
                'successful': successful_updates,
                'failed': failed_updates
            }
            
        except Exception as e:
            logger.error(f"Error in sync_order_status_to_tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error en sincronización de estados: {str(e)}'
            }
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de sincronización."""
        try:
            # Estadísticas de mapeos
            customer_mappings = CustomerMapping.objects.all()
            product_mappings = ProductMapping.objects.all()
            order_mappings = OrderMapping.objects.all()
            
            # Logs de sincronización recientes
            recent_logs = SyncLog.objects.filter(
                started_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).order_by('-started_at')[:10]
            
            stats = {
                'customer_mappings': {
                    'total': customer_mappings.count(),
                    'synced': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.SYNCED).count(),
                    'pending': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.PENDING).count(),
                    'error': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.ERROR).count()
                },
                'product_mappings': {
                    'total': product_mappings.count(),
                    'synced': product_mappings.filter(sync_status=ProductMapping.SyncStatus.SYNCED).count(),
                    'pending': product_mappings.filter(sync_status=ProductMapping.SyncStatus.PENDING).count(),
                    'error': product_mappings.filter(sync_status=ProductMapping.SyncStatus.ERROR).count()
                },
                'order_mappings': {
                    'total': order_mappings.count(),
                    'synced': order_mappings.filter(sync_status=OrderMapping.SyncStatus.SYNCED).count(),
                    'pending': order_mappings.filter(sync_status=OrderMapping.SyncStatus.PENDING).count(),
                    'error': order_mappings.filter(sync_status=OrderMapping.SyncStatus.ERROR).count()
                },
                'recent_syncs': [
                    {
                        'id': log.id,
                        'type': log.get_sync_type_display(),
                        'direction': log.get_direction_display(),
                        'status': log.get_status_display(),
                        'started_at': log.started_at,
                        'completed_at': log.completed_at,
                        'total_items': log.total_items,
                        'successful_items': log.successful_items,
                        'failed_items': log.failed_items
                    }
                    for log in recent_logs
                ]
            }
            
            return {
                'success': True,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas: {str(e)}'
            } 