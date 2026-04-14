"""
Servicio de sincronización periódica para mantener datos actualizados.
"""

import logging
from typing import Dict, Any, List
from django.utils import timezone
from datetime import timedelta

from ..models import TiendanubeConfig, AdministraNETConfig, CustomerMapping, SyncLog
from .sync_service import TiendanubeAdministraNETSyncService
from .tiendanube_service import TiendanubeService
from .adminet_service import AdministraNETService

logger = logging.getLogger(__name__)


class PeriodicSyncService:
    """
    Servicio para sincronización periódica de datos entre TiendaNube y AdministraNET.
    """
    
    def __init__(self, tiendanube_config: TiendanubeConfig, adminet_config: AdministraNETConfig):
        self.tiendanube_config = tiendanube_config
        self.adminet_config = adminet_config
        self.sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        self.tiendanube_service = TiendanubeService(tiendanube_config)
        be = (adminet_config.database or "").strip()
        self.adminet_service = AdministraNETService(adminet_config, base_empresa=be)
    
    def sync_customer_updates_from_tiendanube(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Sincronizar actualizaciones de clientes desde TiendaNube.
        
        Args:
            hours_back: Horas hacia atrás para buscar clientes modificados
            
        Returns:
            Dict con resultado de la sincronización
        """
        try:
            logger.info(f"🔄 Iniciando sincronización periódica de clientes (últimas {hours_back}h)")
            
            # Crear log de sincronización
            sync_log = SyncLog.objects.create(
                sync_type=SyncLog.SyncType.CUSTOMER,
                direction=SyncLog.SyncDirection.TO_ADMINET,
                status=SyncLog.Status.IN_PROGRESS,
                tiendanube_config=self.tiendanube_config,
                adminet_config=self.adminet_config
            )
            
            # Obtener clientes modificados recientemente en TiendaNube
            cutoff_time = timezone.now() - timedelta(hours=hours_back)
            
            # Obtener todos los clientes de TiendaNube
            tiendanube_result = self.tiendanube_service.get_customers(limit=1000)
            if not tiendanube_result['success']:
                sync_log.complete_sync(False, tiendanube_result['message'])
                return tiendanube_result
            
            customers = tiendanube_result['customers']
            sync_log.total_items = len(customers)
            sync_log.save()
            
            successful_syncs = 0
            failed_syncs = 0
            skipped_syncs = 0
            
            for customer in customers:
                try:
                    customer_id = customer['id']
                    customer_updated_at = customer.get('updated_at', '')
                    
                    # Verificar si el cliente fue modificado recientemente
                    if customer_updated_at:
                        try:
                            from dateutil import parser
                            updated_time = parser.parse(customer_updated_at)
                            if updated_time.replace(tzinfo=timezone.utc) < cutoff_time:
                                skipped_syncs += 1
                                continue
                        except:
                            # Si no se puede parsear la fecha, procesar de todas formas
                            pass
                    
                    # Buscar mapeo existente
                    mapping = CustomerMapping.objects.filter(tiendanube_id=customer_id).first()
                    
                    if mapping and mapping.adminet_codigo:
                        # Verificar si hay cambios significativos
                        has_changes = (
                            mapping.tiendanube_email != customer.get('email', '') or
                            mapping.tiendanube_first_name != customer.get('name', '') or
                            mapping.tiendanube_phone != customer.get('phone', '') or
                            mapping.tiendanube_address != customer.get('address', '')
                        )
                        
                        if has_changes:
                            # Actualizar en AdministraNET
                            adminet_data = {
                                'nombre_cliente': customer.get('name', ''),
                                'Email': customer.get('email', ''),
                                'telefono': customer.get('phone', ''),
                                'Calle': customer.get('address', ''),
                                'CUIT': customer.get('document', ''),
                                'Estado': 'Activo'
                            }
                            
                            result = self.adminet_service.update_customer(mapping.adminet_codigo, adminet_data)
                            if result['success']:
                                # Actualizar mapeo local
                                mapping.tiendanube_email = customer.get('email', '')
                                mapping.tiendanube_first_name = customer.get('name', '')
                                mapping.tiendanube_phone = customer.get('phone', '')
                                mapping.tiendanube_address = customer.get('address', '')
                                mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                                mapping.last_synced = timezone.now()
                                mapping.save()
                                
                                successful_syncs += 1
                                logger.info(f"✅ Cliente {customer.get('name')} actualizado en AdministraNET")
                            else:
                                mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                                mapping.error_message = result['message']
                                mapping.save()
                                failed_syncs += 1
                                logger.error(f"❌ Error actualizando cliente {customer.get('name')}: {result['message']}")
                        else:
                            skipped_syncs += 1
                    else:
                        # Cliente nuevo - crear mapeo y sincronizar
                        mapping, created = CustomerMapping.objects.get_or_create(
                            tiendanube_id=customer_id,
                            defaults={
                                'tiendanube_email': customer.get('email', ''),
                                'tiendanube_first_name': customer.get('name', ''),
                                'tiendanube_phone': customer.get('phone', ''),
                                'tiendanube_address': customer.get('address', ''),
                                'sync_status': CustomerMapping.SyncStatus.PENDING
                            }
                        )
                        
                        if created:
                            # Sincronizar a AdministraNET
                            adminet_data = {
                                'nombre_cliente': customer.get('name', ''),
                                'Email': customer.get('email', ''),
                                'telefono': customer.get('phone', ''),
                                'Calle': customer.get('address', ''),
                                'CUIT': customer.get('document', ''),
                                'Estado': 'Activo'
                            }
                            
                            result = self.adminet_service.create_customer(adminet_data)
                            if result['success']:
                                mapping.adminet_codigo = result.get('customer_id')
                                mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                                mapping.last_synced = timezone.now()
                                mapping.save()
                                
                                successful_syncs += 1
                                logger.info(f"✅ Cliente {customer.get('name')} creado en AdministraNET")
                            else:
                                mapping.sync_status = CustomerMapping.SyncStatus.ERROR
                                mapping.error_message = result['message']
                                mapping.save()
                                failed_syncs += 1
                                logger.error(f"❌ Error creando cliente {customer.get('name')}: {result['message']}")
                        else:
                            skipped_syncs += 1
                    
                    sync_log.processed_items += 1
                    sync_log.save()
                    
                except Exception as e:
                    logger.error(f"Error procesando cliente {customer.get('id')}: {e}")
                    failed_syncs += 1
                    sync_log.processed_items += 1
                    sync_log.save()
            
            # Completar log de sincronización
            sync_log.complete_sync(True, f"Sincronización periódica completada: {successful_syncs} exitosas, {failed_syncs} fallidas, {skipped_syncs} omitidas")
            
            return {
                'success': True,
                'message': f'Sincronización periódica completada: {successful_syncs} exitosas, {failed_syncs} fallidas, {skipped_syncs} omitidas',
                'sync_log_id': sync_log.id,
                'total_processed': len(customers),
                'successful': successful_syncs,
                'failed': failed_syncs,
                'skipped': skipped_syncs
            }
            
        except Exception as e:
            logger.error(f"Error en sincronización periódica: {e}")
            if 'sync_log' in locals():
                sync_log.complete_sync(False, str(e))
            return {
                'success': False,
                'message': f'Error en sincronización periódica: {str(e)}'
            }
    
    def validate_customer_data_consistency(self) -> Dict[str, Any]:
        """
        Validar consistencia de datos entre TiendaNube y AdministraNET.
        
        Returns:
            Dict con resultado de la validación
        """
        try:
            logger.info("🔍 Iniciando validación de consistencia de datos de clientes")
            
            # Obtener todos los mapeos de clientes
            mappings = CustomerMapping.objects.filter(
                tiendanube_id__isnull=False,
                adminet_codigo__isnull=False
            )
            
            inconsistencies = []
            total_checked = 0
            
            for mapping in mappings:
                try:
                    # Obtener datos de TiendaNube
                    tiendanube_result = self.tiendanube_service.get_customer(mapping.tiendanube_id)
                    if not tiendanube_result['success']:
                        inconsistencies.append({
                            'mapping_id': mapping.id,
                            'tiendanube_id': mapping.tiendanube_id,
                            'adminet_codigo': mapping.adminet_codigo,
                            'issue': 'No se pudo obtener datos de TiendaNube',
                            'error': tiendanube_result['message']
                        })
                        continue
                    
                    tiendanube_customer = tiendanube_result['customer']
                    
                    # Obtener datos de AdministraNET
                    adminet_result = self.adminet_service.get_customer(mapping.adminet_codigo)
                    if not adminet_result['success']:
                        inconsistencies.append({
                            'mapping_id': mapping.id,
                            'tiendanube_id': mapping.tiendanube_id,
                            'adminet_codigo': mapping.adminet_codigo,
                            'issue': 'No se pudo obtener datos de AdministraNET',
                            'error': adminet_result['message']
                        })
                        continue
                    
                    adminet_customer = adminet_result['customer']
                    
                    # Verificar inconsistencias
                    customer_inconsistencies = []
                    
                    # Verificar email
                    if tiendanube_customer.get('email') != adminet_customer.get('Email'):
                        customer_inconsistencies.append({
                            'field': 'email',
                            'tiendanube': tiendanube_customer.get('email'),
                            'adminet': adminet_customer.get('Email')
                        })
                    
                    # Verificar nombre
                    if tiendanube_customer.get('name') != adminet_customer.get('nombre_cliente'):
                        customer_inconsistencies.append({
                            'field': 'name',
                            'tiendanube': tiendanube_customer.get('name'),
                            'adminet': adminet_customer.get('nombre_cliente')
                        })
                    
                    # Verificar teléfono
                    if tiendanube_customer.get('phone') != adminet_customer.get('telefono'):
                        customer_inconsistencies.append({
                            'field': 'phone',
                            'tiendanube': tiendanube_customer.get('phone'),
                            'adminet': adminet_customer.get('telefono')
                        })
                    
                    if customer_inconsistencies:
                        inconsistencies.append({
                            'mapping_id': mapping.id,
                            'tiendanube_id': mapping.tiendanube_id,
                            'adminet_codigo': mapping.adminet_codigo,
                            'inconsistencies': customer_inconsistencies
                        })
                    
                    total_checked += 1
                    
                except Exception as e:
                    logger.error(f"Error validando mapeo {mapping.id}: {e}")
                    inconsistencies.append({
                        'mapping_id': mapping.id,
                        'tiendanube_id': mapping.tiendanube_id,
                        'adminet_codigo': mapping.adminet_codigo,
                        'issue': 'Error durante la validación',
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'message': f'Validación completada: {len(inconsistencies)} inconsistencias encontradas de {total_checked} clientes verificados',
                'total_checked': total_checked,
                'inconsistencies': inconsistencies,
                'inconsistency_count': len(inconsistencies)
            }
            
        except Exception as e:
            logger.error(f"Error en validación de consistencia: {e}")
            return {
                'success': False,
                'message': f'Error en validación de consistencia: {str(e)}'
            }
    
    def fix_customer_inconsistencies(self, inconsistencies: List[Dict[str, Any]], 
                                   prefer_tiendanube: bool = True) -> Dict[str, Any]:
        """
        Corregir inconsistencias de datos de clientes.
        
        Args:
            inconsistencies: Lista de inconsistencias encontradas
            prefer_tiendanube: Si True, usar datos de TiendaNube como fuente de verdad
            
        Returns:
            Dict con resultado de las correcciones
        """
        try:
            logger.info(f"🔧 Iniciando corrección de {len(inconsistencies)} inconsistencias")
            
            fixed_count = 0
            failed_count = 0
            errors = []
            
            for inconsistency in inconsistencies:
                try:
                    mapping_id = inconsistency['mapping_id']
                    mapping = CustomerMapping.objects.get(id=mapping_id)
                    
                    if prefer_tiendanube:
                        # Usar datos de TiendaNube como fuente de verdad
                        tiendanube_result = self.tiendanube_service.get_customer(mapping.tiendanube_id)
                        if tiendanube_result['success']:
                            customer_data = tiendanube_result['customer']
                            
                            adminet_data = {
                                'nombre_cliente': customer_data.get('name', ''),
                                'Email': customer_data.get('email', ''),
                                'telefono': customer_data.get('phone', ''),
                                'Calle': customer_data.get('address', ''),
                                'CUIT': customer_data.get('document', ''),
                                'Estado': 'Activo'
                            }
                            
                            result = self.adminet_service.update_customer(mapping.adminet_codigo, adminet_data)
                            if result['success']:
                                # Actualizar mapeo local
                                mapping.tiendanube_email = customer_data.get('email', '')
                                mapping.tiendanube_first_name = customer_data.get('name', '')
                                mapping.tiendanube_phone = customer_data.get('phone', '')
                                mapping.tiendanube_address = customer_data.get('address', '')
                                mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                                mapping.last_synced = timezone.now()
                                mapping.save()
                                
                                fixed_count += 1
                                logger.info(f"✅ Inconsistencia corregida para cliente {mapping.tiendanube_id}")
                            else:
                                failed_count += 1
                                errors.append(f"Error actualizando cliente {mapping.tiendanube_id}: {result['message']}")
                        else:
                            failed_count += 1
                            errors.append(f"Error obteniendo datos de TiendaNube para cliente {mapping.tiendanube_id}")
                    else:
                        # Usar datos de AdministraNET como fuente de verdad
                        adminet_result = self.adminet_service.get_customer(mapping.adminet_codigo)
                        if adminet_result['success']:
                            customer_data = adminet_result['customer']
                            
                            # Actualizar en TiendaNube
                            tiendanube_data = {
                                'name': customer_data.get('nombre_cliente', ''),
                                'email': customer_data.get('Email', ''),
                                'phone': customer_data.get('telefono', ''),
                                'address': customer_data.get('Calle', ''),
                                'document': customer_data.get('CUIT', '')
                            }
                            
                            result = self.tiendanube_service.update_customer(mapping.tiendanube_id, tiendanube_data)
                            if result['success']:
                                # Actualizar mapeo local
                                mapping.tiendanube_email = customer_data.get('Email', '')
                                mapping.tiendanube_first_name = customer_data.get('nombre_cliente', '')
                                mapping.tiendanube_phone = customer_data.get('telefono', '')
                                mapping.tiendanube_address = customer_data.get('Calle', '')
                                mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
                                mapping.last_synced = timezone.now()
                                mapping.save()
                                
                                fixed_count += 1
                                logger.info(f"✅ Inconsistencia corregida para cliente {mapping.tiendanube_id}")
                            else:
                                failed_count += 1
                                errors.append(f"Error actualizando cliente {mapping.tiendanube_id} en TiendaNube: {result['message']}")
                        else:
                            failed_count += 1
                            errors.append(f"Error obteniendo datos de AdministraNET para cliente {mapping.tiendanube_id}")
                
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error procesando inconsistencia {inconsistency.get('mapping_id')}: {str(e)}")
            
            return {
                'success': True,
                'message': f'Corrección completada: {fixed_count} corregidas, {failed_count} fallidas',
                'fixed_count': fixed_count,
                'failed_count': failed_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error en corrección de inconsistencias: {e}")
            return {
                'success': False,
                'message': f'Error en corrección de inconsistencias: {str(e)}'
            }


