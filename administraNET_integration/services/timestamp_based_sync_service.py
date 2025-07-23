import logging
from django.utils import timezone
from django.db import transaction
from django.apps import apps
from .bidirectional_sync_service import BidirectionalSyncService
from ..models import SyncLog, TableMapping, SyncTimestampLog, SyncTimestampConfig

logger = logging.getLogger(__name__)


class TimestampBasedBidirectionalSyncService(BidirectionalSyncService):
    """
    Servicio de sincronización bidireccional con resolución de conflictos basada en timestamps
    Gana siempre el registro más reciente en ambas direcciones
    """
    
    def __init__(self, config):
        """
        Inicializar servicio con configuración
        
        Args:
            config: Instancia de AdministraNETConfig
        """
        super().__init__(config)
        self.timestamp_configs = self._load_timestamp_configs()
    
    def _load_timestamp_configs(self):
        """Cargar configuraciones de timestamp por tipo de sincronización"""
        configs = {}
        for config in SyncTimestampConfig.objects.filter(is_active=True):
            configs[config.sync_type] = config
        return configs
    
    def sync_bidirectional(self, sync_type, direction='BOTH', sync_log=None):
        """
        Sincronización bidireccional con resolución de conflictos por timestamp
        
        Args:
            sync_type (str): Tipo de sincronización (PRODUCTS, CUSTOMERS, STOCK, ORDERS)
            direction (str): Dirección de sincronización (TO_SYNAP, FROM_SYNAP, BOTH)
            sync_log: Instancia de SyncLog para registrar progreso
            
        Returns:
            dict: Resultado de la sincronización
        """
        if not sync_log:
            sync_log = SyncLog.objects.create(
                sync_type=sync_type,
                status='PENDING'
            )
        
        try:
            sync_log.status = 'RUNNING'
            sync_log.save()
            
            results = {
                'to_synap': {'success': False, 'processed': 0, 'created': 0, 'updated': 0, 'failed': 0, 'conflicts_resolved': 0},
                'from_synap': {'success': False, 'processed': 0, 'created': 0, 'updated': 0, 'failed': 0, 'conflicts_resolved': 0}
            }
            
            # Sincronización hacia Synap
            if direction in ['TO_SYNAP', 'BOTH']:
                results['to_synap'] = self._sync_to_synap_with_timestamp_resolution(sync_type, sync_log)
            
            # Sincronización desde Synap
            if direction in ['FROM_SYNAP', 'BOTH']:
                results['from_synap'] = self._sync_from_synap_with_timestamp_resolution(sync_type, sync_log)
            
            # Calcular totales
            total_processed = results['to_synap']['processed'] + results['from_synap']['processed']
            total_created = results['to_synap']['created'] + results['from_synap']['created']
            total_updated = results['to_synap']['updated'] + results['from_synap']['updated']
            total_failed = results['to_synap']['failed'] + results['from_synap']['failed']
            total_conflicts = results['to_synap']['conflicts_resolved'] + results['from_synap']['conflicts_resolved']
            
            # Actualizar log
            sync_log.records_processed = total_processed
            sync_log.records_created = total_created
            sync_log.records_updated = total_updated
            sync_log.records_failed = total_failed
            sync_log.details = {
                'direction': direction,
                'results': results,
                'conflicts_resolved': total_conflicts
            }
            sync_log.mark_completed(success=True)
            
            # Actualizar configuración
            self.config.last_sync = timezone.now()
            self.config.save()
            
            return {
                'success': True,
                'direction': direction,
                'results': results,
                'total_processed': total_processed,
                'total_created': total_created,
                'total_updated': total_updated,
                'total_failed': total_failed,
                'total_conflicts_resolved': total_conflicts
            }
            
        except Exception as e:
            error_msg = f"Error en sincronización bidireccional con timestamps {sync_type}: {str(e)}"
            logger.error(error_msg)
            sync_log.mark_completed(success=False, error_message=error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _sync_to_synap_with_timestamp_resolution(self, sync_type, sync_log):
        """
        Sincronización hacia Synap con resolución por timestamp
        
        Args:
            sync_type (str): Tipo de sincronización
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        try:
            mapping = self._get_mapping(sync_type)
            if not mapping:
                return {'success': False, 'error': f'No hay mapeo configurado para {sync_type}'}
            
            # Obtener datos de administraNET
            admin_data = self.connection_service.get_table_data(mapping.administraNET_table)
            
            processed = 0
            created = 0
            updated = 0
            failed = 0
            conflicts_resolved = 0
            
            # Obtener modelo de Synap
            synap_model = self._get_synap_model(mapping.synap_model)
            
            for admin_record in admin_data:
                try:
                    processed += 1
                    
                    # Mapear campos
                    synap_data = self._map_fields(admin_record, mapping.field_mappings)
                    
                    # Buscar registro existente o crear nuevo
                    existing_record = self._find_existing_record(synap_model, synap_data, sync_type)
                    
                    if existing_record:
                        # Verificar si hay conflictos de timestamp
                        if self._has_timestamp_conflict(existing_record, admin_record):
                            resolution = self._resolve_timestamp_conflict(existing_record, admin_record)
                            
                            if resolution == 'ADMINET_WINS':
                                # administraNET es más reciente - actualizar Synap
                                self._update_record_from_adminet(existing_record, synap_data)
                                updated += 1
                                conflicts_resolved += 1
                                
                                # Log del conflicto
                                self._log_timestamp_conflict(
                                    sync_log, sync_type, existing_record.id,
                                    existing_record.updated_at, admin_record.get('fecha_mod'),
                                    'ADMINET_WINS', list(synap_data.keys())
                                )
                                
                            elif resolution == 'SYNAP_WINS':
                                # Synap es más reciente - saltar este registro
                                logger.info(f"Saltando {sync_type} {existing_record.id}: Synap más reciente")
                                conflicts_resolved += 1
                                
                                # Log del conflicto
                                self._log_timestamp_conflict(
                                    sync_log, sync_type, existing_record.id,
                                    existing_record.updated_at, admin_record.get('fecha_mod'),
                                    'SYNAP_WINS', []
                                )
                                continue
                            else:
                                # NO_CHANGE - mantener estado actual
                                logger.info(f"No cambios en {sync_type} {existing_record.id}: mismos timestamps")
                                continue
                        else:
                            # Sin conflictos, actualizar normalmente
                            self._update_record_safe(existing_record, synap_data)
                            updated += 1
                    else:
                        # Crear nuevo registro
                        synap_model.objects.create(**synap_data)
                        created += 1
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error procesando {sync_type} hacia Synap: {e}")
            
            return {
                'success': True,
                'processed': processed,
                'created': created,
                'updated': updated,
                'failed': failed,
                'conflicts_resolved': conflicts_resolved
            }
            
        except Exception as e:
            error_msg = f"Error en sincronización hacia Synap con timestamps {sync_type}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'processed': 0,
                'created': 0,
                'updated': 0,
                'failed': 0,
                'conflicts_resolved': 0
            }

    def _sync_from_synap_with_timestamp_resolution(self, sync_type, sync_log):
        """
        Sincronización desde Synap con resolución por timestamp
        
        Args:
            sync_type (str): Tipo de sincronización
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        try:
            mapping = self._get_mapping(sync_type)
            if not mapping:
                return {'success': False, 'error': f'No hay mapeo configurado para {sync_type}'}
            
            # Obtener datos de Synap
            synap_model = self._get_synap_model(mapping.synap_model)
            synap_data = list(synap_model.objects.all())
            
            processed = 0
            created = 0
            updated = 0
            failed = 0
            conflicts_resolved = 0
            
            for synap_record in synap_data:
                try:
                    processed += 1
                    
                    # Mapear campos hacia administraNET
                    admin_data = self._map_fields_reverse(synap_record, mapping.field_mappings)
                    
                    # Buscar registro existente en administraNET
                    existing_admin_record = self._find_existing_admin_record(mapping.administraNET_table, admin_data, sync_type)
                    
                    if existing_admin_record:
                        # Verificar si hay conflictos de timestamp
                        if self._has_timestamp_conflict_reverse(synap_record, existing_admin_record):
                            resolution = self._resolve_timestamp_conflict_reverse(synap_record, existing_admin_record)
                            
                            if resolution == 'SYNAP_WINS':
                                # Synap es más reciente - actualizar administraNET
                                self._update_admin_record_from_synap(mapping.administraNET_table, existing_admin_record, admin_data)
                                updated += 1
                                conflicts_resolved += 1
                                
                                # Log del conflicto
                                self._log_timestamp_conflict(
                                    sync_log, sync_type, synap_record.id,
                                    synap_record['updated_at'], existing_admin_record.get('fecha_mod'),
                                    'SYNAP_WINS', list(admin_data.keys())
                                )
                                
                            elif resolution == 'ADMINET_WINS':
                                # administraNET es más reciente - saltar este registro
                                logger.info(f"Saltando {sync_type} {synap_record.id}: administraNET más reciente")
                                conflicts_resolved += 1
                                
                                # Log del conflicto
                                self._log_timestamp_conflict(
                                    sync_log, sync_type, synap_record.id,
                                    synap_record['updated_at'], existing_admin_record.get('fecha_mod'),
                                    'ADMINET_WINS', []
                                )
                                continue
                            else:
                                # NO_CHANGE - mantener estado actual
                                logger.info(f"No cambios en {sync_type} {synap_record.id}: mismos timestamps")
                                continue
                        else:
                            # Sin conflictos, actualizar normalmente
                            self._update_admin_record_safe(mapping.administraNET_table, existing_admin_record, admin_data)
                            updated += 1
                    else:
                        # Crear nuevo registro en administraNET
                        self.connection_service.insert_record(mapping.administraNET_table, admin_data)
                        created += 1
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error procesando {sync_type} desde Synap: {e}")
            
            return {
                'success': True,
                'processed': processed,
                'created': created,
                'updated': updated,
                'failed': failed,
                'conflicts_resolved': conflicts_resolved
            }
            
        except Exception as e:
            error_msg = f"Error en sincronización desde Synap con timestamps {sync_type}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'processed': 0,
                'created': 0,
                'updated': 0,
                'failed': 0,
                'conflicts_resolved': 0
            }

    def _has_timestamp_conflict(self, synap_record, admin_record):
        """
        Verificar si hay conflicto de timestamp entre Synap y administraNET
        
        Args:
            synap_record: Registro de Synap
            admin_record: Registro de administraNET
            
        Returns:
            bool: True si hay conflicto
        """
        try:
            synap_updated = synap_record.updated_at
            adminet_updated = admin_record.get('fecha_mod')
            
            if not synap_updated or not adminet_updated:
                return False
            
            # Convertir a datetime si es necesario
            if isinstance(adminet_updated, str):
                from django.utils.dateparse import parse_datetime
                adminet_updated = parse_datetime(adminet_updated)
            
            # Hay conflicto si ambos registros fueron modificados
            return synap_updated and adminet_updated
        except Exception as e:
            logger.error(f"Error verificando conflicto de timestamp: {e}")
            return False

    def _has_timestamp_conflict_reverse(self, synap_record, admin_record):
        """
        Verificar si hay conflicto de timestamp (desde Synap hacia administraNET)
        
        Args:
            synap_record: Registro de Synap
            admin_record: Registro de administraNET
            
        Returns:
            bool: True si hay conflicto
        """
        try:
            synap_updated = synap_record.updated_at
            adminet_updated = admin_record.get('fecha_mod')
            
            if not synap_updated or not adminet_updated:
                return False
            
            # Convertir a datetime si es necesario
            if isinstance(adminet_updated, str):
                from django.utils.dateparse import parse_datetime
                adminet_updated = parse_datetime(adminet_updated)
            
            # Hay conflicto si ambos registros fueron modificados
            return synap_updated and adminet_updated
        except Exception as e:
            logger.error(f"Error verificando conflicto de timestamp reverse: {e}")
            return False

    def _resolve_timestamp_conflict(self, synap_record, admin_record):
        """
        Resolver conflicto de timestamp: gana el más reciente
        
        Args:
            synap_record: Registro de Synap
            admin_record: Registro de administraNET
            
        Returns:
            str: 'ADMINET_WINS', 'SYNAP_WINS', o 'NO_CHANGE'
        """
        try:
            synap_updated = synap_record.updated_at
            adminet_updated = admin_record.get('fecha_mod')
            
            if not synap_updated or not adminet_updated:
                return 'NO_CHANGE'
            
            # Convertir a datetime si es necesario
            if isinstance(adminet_updated, str):
                from django.utils.dateparse import parse_datetime
                adminet_updated = parse_datetime(adminet_updated)
            
            if synap_updated > adminet_updated:
                return 'SYNAP_WINS'
            elif adminet_updated > synap_updated:
                return 'ADMINET_WINS'
            else:
                return 'NO_CHANGE'
                
        except Exception as e:
            logger.error(f"Error resolviendo conflicto de timestamp: {e}")
            return 'NO_CHANGE'

    def _resolve_timestamp_conflict_reverse(self, synap_record, admin_record):
        """
        Resolver conflicto de timestamp (desde Synap hacia administraNET)
        
        Args:
            synap_record: Registro de Synap
            admin_record: Registro de administraNET
            
        Returns:
            str: 'ADMINET_WINS', 'SYNAP_WINS', o 'NO_CHANGE'
        """
        try:
            synap_updated = synap_record.updated_at
            adminet_updated = admin_record.get('fecha_mod')
            
            if not synap_updated or not adminet_updated:
                return 'NO_CHANGE'
            
            # Convertir a datetime si es necesario
            if isinstance(adminet_updated, str):
                from django.utils.dateparse import parse_datetime
                adminet_updated = parse_datetime(adminet_updated)
            
            if synap_updated > adminet_updated:
                return 'SYNAP_WINS'
            elif adminet_updated > synap_updated:
                return 'ADMINET_WINS'
            else:
                return 'NO_CHANGE'
                
        except Exception as e:
            logger.error(f"Error resolviendo conflicto de timestamp reverse: {e}")
            return 'NO_CHANGE'

    def _update_record_from_adminet(self, synap_record, synap_data):
        """
        Actualizar registro de Synap con datos de administraNET
        
        Args:
            synap_record: Registro de Synap a actualizar
            synap_data: Datos de administraNET mapeados
        """
        try:
            for field, value in synap_data.items():
                if hasattr(synap_record, field):
                    setattr(synap_record, field, value)
            
            # Actualizar timestamp de sincronización
            if hasattr(synap_record, 'last_synced_with_adminet'):
                synap_record.last_synced_with_adminet = timezone.now()
            
            synap_record.save()
            
        except Exception as e:
            logger.error(f"Error actualizando registro desde administraNET: {e}")
            raise

    def _update_admin_record_from_synap(self, table_name, admin_record, admin_data):
        """
        Actualizar registro de administraNET con datos de Synap
        
        Args:
            table_name: Nombre de la tabla en administraNET
            admin_record: Registro de administraNET a actualizar
            admin_data: Datos de Synap mapeados
        """
        try:
            # Agregar timestamp de sincronización
            admin_data['last_synced_with_synap'] = timezone.now()
            
            # Actualizar registro en administraNET
            self.connection_service.update_record(table_name, admin_record['id'], admin_data)
            
        except Exception as e:
            logger.error(f"Error actualizando registro en administraNET: {e}")
            raise

    def _update_record_safe(self, synap_record, synap_data):
        """
        Actualizar registro de Synap de forma segura
        
        Args:
            synap_record: Registro de Synap a actualizar
            synap_data: Datos a actualizar
        """
        try:
            for field, value in synap_data.items():
                if hasattr(synap_record, field):
                    setattr(synap_record, field, value)
            
            # Actualizar timestamp de sincronización
            if hasattr(synap_record, 'last_synced_with_adminet'):
                synap_record.last_synced_with_adminet = timezone.now()
            
            synap_record.save()
            
        except Exception as e:
            logger.error(f"Error actualizando registro de forma segura: {e}")
            raise

    def _log_timestamp_conflict(self, sync_log, record_type, record_id, synap_timestamp, adminet_timestamp, winner, fields_updated):
        """
        Registrar conflicto de timestamp resuelto
        
        Args:
            sync_log: Instancia de SyncLog
            record_type: Tipo de registro
            record_id: ID del registro
            synap_timestamp: Timestamp de Synap
            adminet_timestamp: Timestamp de administraNET
            winner: Quién ganó el conflicto
            fields_updated: Campos actualizados
        """
        try:
            SyncTimestampLog.objects.create(
                sync_log=sync_log,
                record_type=record_type,
                record_id=record_id,
                synap_timestamp=synap_timestamp,
                adminet_timestamp=adminet_timestamp,
                winner=winner,
                fields_updated=fields_updated,
                resolved_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error registrando conflicto de timestamp: {e}")

    def get_conflict_summary(self, sync_log):
        """
        Obtener resumen de conflictos de timestamp
        
        Args:
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resumen de conflictos
        """
        try:
            conflicts = SyncTimestampLog.objects.filter(sync_log=sync_log)
            
            summary = {
                'total_conflicts': conflicts.count(),
                'adminet_wins': conflicts.filter(winner='ADMINET_WINS').count(),
                'synap_wins': conflicts.filter(winner='SYNAP_WINS').count(),
                'no_change': conflicts.filter(winner='NO_CHANGE').count(),
                'conflicts_by_type': {}
            }
            
            # Agrupar por tipo de registro
            for conflict in conflicts:
                record_type = conflict.record_type
                if record_type not in summary['conflicts_by_type']:
                    summary['conflicts_by_type'][record_type] = {
                        'total': 0,
                        'adminet_wins': 0,
                        'synap_wins': 0,
                        'no_change': 0
                    }
                
                summary['conflicts_by_type'][record_type]['total'] += 1
                summary['conflicts_by_type'][record_type][f"{conflict.winner.lower()}"] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de conflictos: {e}")
            return {} 