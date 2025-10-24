import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db import transaction, models

from ..models import CustomerMapping, AdministraNETConfig, SyncLog
from .adminet_service import AdministraNETService

logger = logging.getLogger(__name__)


class CustomerSyncService:
    """
    Servicio para sincronizar clientes desde AdministraNET hacia Synap.
    """
    
    def __init__(self, adminet_config: AdministraNETConfig):
        self.adminet_config = adminet_config
        self.adminet_service = AdministraNETService(adminet_config)
    
    def sync_customers_from_adminet(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Sincroniza clientes desde AdministraNET hacia Synap.
        
        Args:
            limit: Número máximo de clientes a sincronizar
            offset: Desplazamiento para paginación
            
        Returns:
            Dict con el resultado de la sincronización
        """
        try:
            # Crear log de sincronización
            sync_log = SyncLog.objects.create(
                sync_type=SyncLog.SyncType.CUSTOMER,
                direction=SyncLog.SyncDirection.FROM_ADMINET,
                status=SyncLog.Status.IN_PROGRESS,
                started_at=timezone.now(),
                total_items=0,
                processed_items=0,
                successful_items=0,
                failed_items=0
            )
            
            logger.info(f"🔄 Iniciando sincronización de clientes desde AdministraNET (limit={limit}, offset={offset})")
            
            # Obtener clientes de AdministraNET
            adminet_customers = self._get_adminet_customers(limit, offset)
            
            if not adminet_customers['success']:
                sync_log.status = SyncLog.Status.FAILED
                sync_log.error_message = adminet_customers['message']
                sync_log.completed_at = timezone.now()
                sync_log.save()
                return adminet_customers
            
            customers_data = adminet_customers['data']
            total_customers = len(customers_data)
            
            sync_log.total_items = total_customers
            sync_log.save()
            
            logger.info(f"📊 Encontrados {total_customers} clientes en AdministraNET")
            
            # Procesar cada cliente
            processed = 0
            successful = 0
            failed = 0
            
            for customer_data in customers_data:
                try:
                    result = self._sync_single_customer(customer_data)
                    if result['success']:
                        successful += 1
                        logger.debug(f"✅ Cliente sincronizado: {customer_data.get('Codigo')} - {customer_data.get('nombre_cliente')}")
                    else:
                        failed += 1
                        logger.warning(f"⚠️ Error sincronizando cliente {customer_data.get('Codigo')}: {result['message']}")
                    
                    processed += 1
                    
                    # Actualizar progreso cada 10 clientes
                    if processed % 10 == 0:
                        sync_log.processed_items = processed
                        sync_log.successful_items = successful
                        sync_log.failed_items = failed
                        sync_log.save()
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"❌ Error procesando cliente {customer_data.get('Codigo')}: {str(e)}")
            
            # Finalizar log
            sync_log.processed_items = processed
            sync_log.successful_items = successful
            sync_log.failed_items = failed
            sync_log.status = SyncLog.Status.COMPLETED if failed == 0 else SyncLog.Status.FAILED
            sync_log.completed_at = timezone.now()
            sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
            sync_log.save()
            
            logger.info(f"✅ Sincronización completada: {successful} exitosos, {failed} fallidos")
            
            return {
                'success': True,
                'message': f'Sincronización completada: {successful} exitosos, {failed} fallidos',
                'total_processed': processed,
                'successful': successful,
                'failed': failed,
                'sync_log_id': sync_log.id
            }
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización de clientes: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            }
    
    def _get_adminet_customers(self, limit: int, offset: int) -> Dict[str, Any]:
        """
        Obtiene clientes de AdministraNET.
        """
        try:
            query = """
            SELECT 
                Codigo,
                nombre_cliente,
                Email,
                telefono,
                Calle,
                NroCalle,
                Dpto,
                CodProvincia,
                IDDepartamento,
                IDDistrito,
                CUIT,
                Credito,
                TipoCliente,
                NombreContacto,
                TelefonoContacto,
                CelularContacto,
                EmailContacto
            FROM cliente 
            WHERE Codigo > 0
            ORDER BY Codigo
            LIMIT %s OFFSET %s
            """
            
            result = self.adminet_service.execute_query(query, (limit, offset))
            
            if not result['success']:
                return result
            
            return {
                'success': True,
                'data': result['results'],
                'message': f'Obtenidos {len(result["results"])} clientes de AdministraNET'
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo clientes de AdministraNET: {str(e)}")
            return {
                'success': False,
                'message': f'Error obteniendo clientes: {str(e)}'
            }
    
    def _sync_single_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza un cliente individual desde AdministraNET.
        """
        try:
            adminet_codigo = customer_data.get('Codigo')
            if not adminet_codigo:
                return {'success': False, 'message': 'Código de cliente no encontrado'}
            
            # Buscar si ya existe el mapeo
            existing_mapping = CustomerMapping.objects.filter(
                adminet_codigo=adminet_codigo
            ).first()
            
            if existing_mapping:
                # Actualizar mapeo existente
                return self._update_existing_mapping(existing_mapping, customer_data)
            else:
                # Crear nuevo mapeo
                return self._create_new_mapping(customer_data)
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando cliente individual: {str(e)}")
            return {
                'success': False,
                'message': f'Error sincronizando cliente: {str(e)}'
            }
    
    def _update_existing_mapping(self, mapping: CustomerMapping, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un mapeo existente con datos de AdministraNET.
        """
        try:
            # Actualizar campos de AdministraNET
            mapping.adminet_nombre = customer_data.get('nombre_cliente', '') or ''
            mapping.adminet_email = customer_data.get('Email', '') or ''
            mapping.adminet_telefono = customer_data.get('telefono', '') or ''
            mapping.adminet_calle = customer_data.get('Calle', '') or ''
            mapping.adminet_nro_calle = customer_data.get('NroCalle', '') or ''
            mapping.adminet_dpto = customer_data.get('Dpto', '') or ''
            mapping.adminet_cuit = customer_data.get('CUIT', '') or ''
            mapping.adminet_credito = customer_data.get('Credito', 0) or 0
            
            # Actualizar dirección combinada
            mapping.combine_adminet_address()
            
            # Marcar como sincronizado si no tiene Tiendanube ID
            if not mapping.tiendanube_id:
                mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
            
            mapping.save()
            
            return {
                'success': True,
                'message': f'Cliente {mapping.adminet_codigo} actualizado',
                'action': 'updated'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error actualizando cliente: {str(e)}'
            }
    
    def _create_new_mapping(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo mapeo de cliente.
        """
        try:
            # Crear email único si no existe
            adminet_email = customer_data.get('Email', '') or ''
            if not adminet_email:
                adminet_email = f"adminet_{customer_data.get('Codigo')}@noemail.local"
            
            # Crear nuevo mapeo
            mapping = CustomerMapping.objects.create(
                # Campos de AdministraNET
                adminet_codigo=customer_data.get('Codigo'),
                adminet_nombre=customer_data.get('nombre_cliente', '') or '',
                adminet_email=adminet_email,
                adminet_telefono=customer_data.get('telefono', '') or '',
                adminet_calle=customer_data.get('Calle', '') or '',
                adminet_nro_calle=customer_data.get('NroCalle', '') or '',
                adminet_dpto=customer_data.get('Dpto', '') or '',
                adminet_cuit=customer_data.get('CUIT', '') or '',
                adminet_credito=customer_data.get('Credito', 0) or 0,
                
                # Email de Tiendanube (usar el mismo que AdministraNET)
                tiendanube_email=adminet_email,
                
                # Configuración de sincronización
                sync_status=CustomerMapping.SyncStatus.SYNCED,
                sync_enabled=True,
                sync_direction=CustomerMapping.SyncDirection.ADMINET_TO_TIENDANUBE
            )
            
            # Actualizar dirección combinada
            mapping.combine_adminet_address()
            mapping.save()
            
            return {
                'success': True,
                'message': f'Cliente {mapping.adminet_codigo} creado',
                'action': 'created',
                'mapping_id': mapping.id
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error creando cliente: {str(e)}'
            }
    
    def get_customers_with_adminet_data(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Obtiene clientes que tienen datos de AdministraNET (mapeos reales).
        """
        try:
            # Obtener mapeos que tienen adminet_codigo (datos reales)
            mappings = CustomerMapping.objects.filter(
                adminet_codigo__isnull=False,
                adminet_codigo__gt=0
            ).order_by('-last_sync_at', '-created_at')[offset:offset + limit]
            
            # Convertir a lista de diccionarios para la vista
            customers_data = []
            for mapping in mappings:
                customer_data = {
                    'id': mapping.id,
                    'adminet_codigo': mapping.adminet_codigo,
                    'adminet_nombre': mapping.adminet_nombre,
                    'adminet_email': mapping.adminet_email,
                    'adminet_telefono': mapping.adminet_telefono,
                    'adminet_direccion': mapping.combine_adminet_address(),
                    'tiendanube_id': mapping.tiendanube_id,
                    'tiendanube_email': mapping.tiendanube_email,
                    'tiendanube_name': mapping.tiendanube_name,
                    'sync_status': mapping.sync_status,
                    'sync_enabled': mapping.sync_enabled,
                    'last_synced': mapping.last_synced,
                    'created_at': mapping.created_at,
                    'is_real_data': True  # Marcar como datos reales
                }
                customers_data.append(customer_data)
            
            return {
                'success': True,
                'data': customers_data,
                'total': CustomerMapping.objects.filter(adminet_codigo__isnull=False, adminet_codigo__gt=0).count(),
                'message': f'Obtenidos {len(customers_data)} clientes con datos reales de AdministraNET'
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo clientes con datos reales: {str(e)}")
            return {
                'success': False,
                'message': f'Error obteniendo clientes: {str(e)}',
                'data': []
            }
    
    def get_customers_with_fake_data(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Obtiene clientes que tienen datos ficticios (para comparación).
        """
        try:
            # Obtener mapeos que NO tienen adminet_codigo o tienen códigos ficticios
            mappings = CustomerMapping.objects.filter(
                models.Q(adminet_codigo__isnull=True) | 
                models.Q(adminet_codigo__gte=1000)  # Códigos ficticios >= 1000
            ).order_by('-created_at')[offset:offset + limit]
            
            # Convertir a lista de diccionarios para la vista
            customers_data = []
            for mapping in mappings:
                customer_data = {
                    'id': mapping.id,
                    'adminet_codigo': mapping.adminet_codigo,
                    'adminet_nombre': mapping.adminet_nombre,
                    'adminet_email': mapping.adminet_email,
                    'adminet_telefono': mapping.adminet_telefono,
                    'adminet_direccion': mapping.combine_adminet_address(),
                    'tiendanube_id': mapping.tiendanube_id,
                    'tiendanube_email': mapping.tiendanube_email,
                    'tiendanube_name': mapping.tiendanube_name,
                    'sync_status': mapping.sync_status,
                    'sync_enabled': mapping.sync_enabled,
                    'last_synced': mapping.last_synced,
                    'created_at': mapping.created_at,
                    'is_real_data': False  # Marcar como datos ficticios
                }
                customers_data.append(customer_data)
            
            return {
                'success': True,
                'data': customers_data,
                'total': CustomerMapping.objects.filter(
                    models.Q(adminet_codigo__isnull=True) | 
                    models.Q(adminet_codigo__gte=1000)
                ).count(),
                'message': f'Obtenidos {len(customers_data)} clientes con datos ficticios'
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo clientes ficticios: {str(e)}")
            return {
                'success': False,
                'message': f'Error obteniendo clientes ficticios: {str(e)}',
                'data': [],
                'total': 0
            }

    def get_customers_with_adminet_data(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Obtiene clientes directamente de AdministraNET para mostrar en la vista.
        
        Args:
            limit (int): Límite de clientes a obtener.
            offset (int): Offset para la paginación.
            
        Returns:
            Dict con los datos de clientes de AdministraNET
        """
        try:
            query = """
            SELECT
                Codigo,
                TipoCliente,
                nombre_cliente,
                Calle,
                NroCalle,
                Dpto,
                IDDistrito,
                CodProvincia,
                IDDepartamento,
                telefono,
                Email,
                Fax,
                NombreContacto,
                TelefonoContacto,
                CelularContacto,
                EmailContacto,
                IDIva,
                CUIT,
                Credito
            FROM cliente
            WHERE Codigo > 0
            ORDER BY Codigo
            LIMIT %s OFFSET %s
            """

            result = self.adminet_service.execute_query(query, (limit, offset))

            if not result['success']:
                return {
                    'success': False,
                    'message': result['message'],
                    'data': [],
                    'total': 0
                }

            return {
                'success': True,
                'data': result['results'],
                'total': len(result['results']),
                'message': f'Obtenidos {len(result["results"])} clientes de AdministraNET'
            }

        except Exception as e:
            logger.error(f"❌ Error obteniendo clientes de AdministraNET: {str(e)}")
            return {
                'success': False,
                'message': f'Error obteniendo clientes: {str(e)}',
                'data': [],
                'total': 0
            }
