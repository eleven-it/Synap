import logging
from django.utils import timezone
from django.db import transaction
from django.apps import apps
from .connection_service import AdministraNETConnectionService
from ..models import SyncLog, TableMapping

logger = logging.getLogger(__name__)


class BidirectionalSyncService:
    """
    Servicio para sincronización bidireccional entre administraNET y Synap
    """
    
    def __init__(self, config):
        """
        Inicializar servicio con configuración
        
        Args:
            config: Instancia de AdministraNETConfig
        """
        self.config = config
        self.connection_service = AdministraNETConnectionService(config)
    
    def sync_bidirectional(self, sync_type, direction='BOTH', sync_log=None):
        """
        Sincronización bidireccional por tipo
        
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
                'to_synap': {'success': False, 'processed': 0, 'created': 0, 'updated': 0, 'failed': 0},
                'from_synap': {'success': False, 'processed': 0, 'created': 0, 'updated': 0, 'failed': 0}
            }
            
            # Sincronización hacia Synap
            if direction in ['TO_SYNAP', 'BOTH']:
                results['to_synap'] = self._sync_to_synap(sync_type, sync_log)
            
            # Sincronización desde Synap
            if direction in ['FROM_SYNAP', 'BOTH']:
                results['from_synap'] = self._sync_from_synap(sync_type, sync_log)
            
            # Calcular totales
            total_processed = results['to_synap']['processed'] + results['from_synap']['processed']
            total_created = results['to_synap']['created'] + results['from_synap']['created']
            total_updated = results['to_synap']['updated'] + results['from_synap']['updated']
            total_failed = results['to_synap']['failed'] + results['from_synap']['failed']
            
            # Actualizar log
            sync_log.records_processed = total_processed
            sync_log.records_created = total_created
            sync_log.records_updated = total_updated
            sync_log.records_failed = total_failed
            sync_log.details = {
                'direction': direction,
                'results': results
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
                'total_failed': total_failed
            }
            
        except Exception as e:
            error_msg = f"Error en sincronización bidireccional {sync_type}: {str(e)}"
            logger.error(error_msg)
            sync_log.mark_completed(success=False, error_message=error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _sync_to_synap(self, sync_type, sync_log):
        """
        Sincronizar desde administraNET hacia Synap
        
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
                        # Actualizar registro existente
                        for field, value in synap_data.items():
                            if hasattr(existing_record, field):
                                setattr(existing_record, field, value)
                        existing_record.save()
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
                'failed': failed
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando {sync_type} hacia Synap: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _sync_from_synap(self, sync_type, sync_log):
        """
        Sincronizar desde Synap hacia administraNET
        
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
            synap_data = list(synap_model.objects.all().values())
            
            processed = 0
            created = 0
            updated = 0
            failed = 0
            
            for synap_record in synap_data:
                try:
                    processed += 1
                    
                    # Mapear campos de Synap a administraNET
                    admin_data = self._map_fields_reverse(synap_record, mapping.field_mappings)
                    
                    # Buscar registro existente en administraNET
                    existing_record = self._find_existing_admin_record(
                        mapping.administraNET_table, admin_data, sync_type
                    )
                    
                    if existing_record:
                        # Actualizar registro existente en administraNET
                        self._update_admin_record(mapping.administraNET_table, existing_record, admin_data)
                        updated += 1
                    else:
                        # Crear nuevo registro en administraNET
                        self._create_admin_record(mapping.administraNET_table, admin_data)
                        created += 1
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error procesando {sync_type} desde Synap: {e}")
            
            return {
                'success': True,
                'processed': processed,
                'created': created,
                'updated': updated,
                'failed': failed
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando {sync_type} desde Synap: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def sync_customers_bidirectional(self, direction='BOTH', sync_log=None):
        """
        Sincronización bidireccional específica para clientes
        
        Args:
            direction (str): Dirección de sincronización
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        return self.sync_bidirectional('CUSTOMERS', direction, sync_log)
    
    def sync_products_bidirectional(self, direction='BOTH', sync_log=None):
        """
        Sincronización bidireccional específica para productos
        
        Args:
            direction (str): Dirección de sincronización
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        return self.sync_bidirectional('PRODUCTS', direction, sync_log)
    
    def sync_stock_bidirectional(self, direction='BOTH', sync_log=None):
        """
        Sincronización bidireccional específica para stock
        
        Args:
            direction (str): Dirección de sincronización
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        return self.sync_bidirectional('STOCK', direction, sync_log)
    
    def sync_orders_bidirectional(self, direction='BOTH', sync_log=None):
        """
        Sincronización bidireccional específica para pedidos
        
        Args:
            direction (str): Dirección de sincronización
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        return self.sync_bidirectional('ORDERS', direction, sync_log)
    
    def _find_existing_record(self, synap_model, synap_data, sync_type):
        """
        Buscar registro existente en Synap
        
        Args:
            synap_model: Modelo de Synap
            synap_data (dict): Datos del registro
            sync_type (str): Tipo de sincronización
            
        Returns:
            Model instance or None
        """
        # Estrategias de búsqueda por tipo
        if sync_type == 'CUSTOMERS':
            # Buscar por id_administraNET si está presente
            if 'id_administraNET' in synap_data and synap_data['id_administraNET']:
                return synap_model.objects.filter(id_administraNET=synap_data['id_administraNET']).first()
            # Fallback: buscar por email o nombre
            if 'email' in synap_data and synap_data['email']:
                return synap_model.objects.filter(email=synap_data['email']).first()
            elif 'name' in synap_data and synap_data['name']:
                return synap_model.objects.filter(name=synap_data['name']).first()
        
        elif sync_type == 'PRODUCTS':
            # Buscar por código o SKU
            if 'code' in synap_data:
                return synap_model.objects.filter(code=synap_data['code']).first()
            elif 'sku' in synap_data:
                return synap_model.objects.filter(sku=synap_data['sku']).first()
        
        elif sync_type == 'STOCK':
            # Buscar por producto y ubicación
            if 'product' in synap_data and 'location' in synap_data:
                return synap_model.objects.filter(
                    product=synap_data['product'],
                    location=synap_data['location']
                ).first()
        
        return None
    
    def _find_existing_admin_record(self, table_name, admin_data, sync_type):
        """
        Buscar registro existente en administraNET
        
        Args:
            table_name (str): Nombre de la tabla
            admin_data (dict): Datos del registro
            sync_type (str): Tipo de sincronización
            
        Returns:
            dict or None
        """
        # Estrategias de búsqueda por tipo
        if sync_type == 'CUSTOMERS':
            # Buscar por código o CUIT
            if 'Codigo' in admin_data:
                query = f"SELECT * FROM {table_name} WHERE Codigo = %s"
                return self.connection_service.execute_query(query, [admin_data['Codigo']])
            elif 'CUIT' in admin_data and admin_data['CUIT']:
                query = f"SELECT * FROM {table_name} WHERE CUIT = %s"
                return self.connection_service.execute_query(query, [admin_data['CUIT']])
        
        elif sync_type == 'PRODUCTS':
            # Buscar por código
            if 'codigo' in admin_data:
                query = f"SELECT * FROM {table_name} WHERE codigo = %s"
                return self.connection_service.execute_query(query, [admin_data['codigo']])
        
        return None
    
    def _update_admin_record(self, table_name, existing_record, admin_data):
        """
        Actualizar registro en administraNET
        
        Args:
            table_name (str): Nombre de la tabla
            existing_record: Registro existente
            admin_data (dict): Nuevos datos
        """
        # Construir query de actualización
        set_clause = ", ".join([f"{field} = %s" for field in admin_data.keys()])
        where_clause = f"Codigo = %s"  # Asumiendo que Codigo es la clave primaria
        
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        values = list(admin_data.values()) + [existing_record['Codigo']]
        
        self.connection_service.execute_query(query, values)
    
    def _create_admin_record(self, table_name, admin_data):
        """
        Crear nuevo registro en administraNET
        
        Args:
            table_name (str): Nombre de la tabla
            admin_data (dict): Datos del registro
        """
        # Construir query de inserción
        fields = ", ".join(admin_data.keys())
        placeholders = ", ".join(["%s"] * len(admin_data))
        
        query = f"INSERT INTO {table_name} ({fields}) VALUES ({placeholders})"
        values = list(admin_data.values())
        
        self.connection_service.execute_query(query, values)
    
    def _map_fields_reverse(self, synap_record, field_mappings):
        """
        Mapear campos de Synap a administraNET (dirección inversa)
        
        Args:
            synap_record (dict): Registro de Synap
            field_mappings (dict): Mapeo de campos
            
        Returns:
            dict: Datos mapeados para administraNET
        """
        admin_data = {}
        
        # Crear mapeo inverso
        reverse_mappings = {v: k for k, v in field_mappings.items()}
        
        for synap_field, admin_field in reverse_mappings.items():
            if synap_field in synap_record:
                admin_data[admin_field] = synap_record[synap_field]
        
        return admin_data
    
    def _get_mapping(self, mapping_type):
        """
        Obtener mapeo por tipo
        
        Args:
            mapping_type (str): Tipo de mapeo
            
        Returns:
            TableMapping: Instancia del mapeo o None
        """
        return TableMapping.objects.filter(
            mapping_type=mapping_type,
            is_active=True
        ).first()
    
    def _get_synap_model(self, model_path):
        """
        Obtener modelo de Synap por ruta
        
        Args:
            model_path (str): Ruta del modelo (app.model)
            
        Returns:
            Model: Clase del modelo
        """
        app_label, model_name = model_path.split('.')
        return apps.get_model(app_label, model_name)
    
    def _map_fields(self, admin_record, field_mappings):
        """
        Mapear campos de administraNET a Synap
        
        Args:
            admin_record (dict): Registro de administraNET
            field_mappings (dict): Mapeo de campos
            
        Returns:
            dict: Datos mapeados para Synap
        """
        synap_data = {}
        
        # Procesar campos especiales primero
        processed_fields = set()
        
        # Transformaciones específicas para clientes
        if 'Estado' in admin_record and 'is_active' in field_mappings.values():
            # Transformar Estado a is_active
            synap_field = [k for k, v in field_mappings.items() if v == 'is_active'][0]
            synap_data['is_active'] = admin_record['Estado'] == 'Activo'
            processed_fields.add('Estado')
        
        # Transformar campos de dirección
        address_fields = ['Calle', 'NroCalle', 'Dpto']
        if any(field in admin_record for field in address_fields) and 'address' in field_mappings.values():
            synap_field = [k for k, v in field_mappings.items() if v == 'address'][0]
            address_parts = []
            if admin_record.get('Calle'):
                address_parts.append(admin_record['Calle'])
            if admin_record.get('NroCalle'):
                address_parts.append(admin_record['NroCalle'])
            if admin_record.get('Dpto'):
                address_parts.append(f"Depto: {admin_record['Dpto']}")
            synap_data['address'] = ', '.join(address_parts)
            processed_fields.update(address_fields)
        
        # Transformar campos de notas
        notes_fields = ['Credito', 'Descuento', 'Observaciones']
        if any(field in admin_record for field in notes_fields) and 'notes' in field_mappings.values():
            notes_parts = []
            if admin_record.get('Credito'):
                notes_parts.append(f"Crédito: {admin_record['Credito']}")
            if admin_record.get('Descuento'):
                notes_parts.append(f"Descuento: {admin_record['Descuento']}")
            if admin_record.get('Observaciones'):
                notes_parts.append(f"Obs: {admin_record['Observaciones']}")
            synap_data['notes'] = ' | '.join(notes_parts)
            processed_fields.update(notes_fields)
        
        # Procesar campos normales
        for admin_field, synap_field in field_mappings.items():
            if admin_field not in processed_fields and admin_field in admin_record:
                synap_data[synap_field] = admin_record[admin_field]
        
        # Asegurar campo name requerido
        if 'name' not in synap_data or not synap_data['name']:
            # Usar nombre_cliente como fallback para name
            if 'nombre_cliente' in admin_record and admin_record['nombre_cliente']:
                synap_data['name'] = admin_record['nombre_cliente']
            elif 'nombre_fantasia' in admin_record and admin_record['nombre_fantasia']:
                synap_data['name'] = admin_record['nombre_fantasia']
            else:
                synap_data['name'] = f'Cliente administraNET {admin_record.get("Codigo", "unknown")}'
        
        # Asegurar email requerido
        if 'email' not in synap_data or not synap_data['email']:
            # Generar email temporal basado en el nombre
            if 'nombre_cliente' in admin_record and admin_record['nombre_cliente']:
                # Limpiar nombre para email
                clean_name = ''.join(c for c in admin_record['nombre_cliente'] if c.isalnum() or c.isspace()).strip()
                clean_name = clean_name.replace(' ', '.').lower()
                synap_data['email'] = f"{clean_name}@administranet.local"
            else:
                synap_data['email'] = f"cliente.{admin_record.get('Codigo', 'unknown')}@administranet.local"
        
        # Asegurar teléfono requerido
        if 'phone' not in synap_data or not synap_data['phone']:
            # Usar teléfono de contacto o generar uno temporal
            if 'telefono' in admin_record and admin_record['telefono']:
                synap_data['phone'] = admin_record['telefono']
            elif 'TelefonoContacto' in admin_record and admin_record['TelefonoContacto']:
                synap_data['phone'] = admin_record['TelefonoContacto']
            else:
                synap_data['phone'] = '0000-0000'
        
        # Asegurar móvil requerido
        if 'mobile' not in synap_data or not synap_data['mobile']:
            # Usar celular de contacto o teléfono como fallback
            if 'CelularContacto' in admin_record and admin_record['CelularContacto']:
                synap_data['mobile'] = admin_record['CelularContacto']
            elif 'telefono' in admin_record and admin_record['telefono']:
                synap_data['mobile'] = admin_record['telefono']
            else:
                synap_data['mobile'] = '0000-0000'
        
        # Generar código único basado en id_administraNET
        if 'code' not in synap_data or not synap_data['code']:
            admin_id = synap_data.get('id_administraNET', admin_record.get('Codigo', 'UNK'))
            synap_data['code'] = f'ADM-{admin_id}'
        
        # Asignar empresa por defecto para clientes sincronizados
        if 'empresa' not in synap_data:
            try:
                from core.models import Empresa
                empresa_default = Empresa.objects.filter(nombre__icontains='Test Tiendanube').first()
                if empresa_default:
                    synap_data['empresa'] = empresa_default
                    logger.info(f"Asignando empresa por defecto: {empresa_default.nombre}")
            except Exception as e:
                logger.warning(f"No se pudo asignar empresa por defecto: {e}")
        
        return synap_data
    
    def get_sync_status(self, sync_type=None):
        """
        Obtener estado de sincronización
        
        Args:
            sync_type (str): Tipo de sincronización (opcional)
            
        Returns:
            dict: Estado de sincronización
        """
        query = SyncLog.objects.all()
        if sync_type:
            query = query.filter(sync_type=sync_type)
        
        latest_sync = query.order_by('-started_at').first()
        
        if not latest_sync:
            return {
                'status': 'NEVER_SYNCED',
                'last_sync': None,
                'success_rate': 0
            }
        
        # Calcular tasa de éxito
        total_records = latest_sync.records_processed
        successful_records = latest_sync.records_created + latest_sync.records_updated
        success_rate = (successful_records / total_records * 100) if total_records > 0 else 0
        
        return {
            'status': latest_sync.status,
            'last_sync': latest_sync.started_at,
            'success_rate': round(success_rate, 2),
            'processed': latest_sync.records_processed,
            'created': latest_sync.records_created,
            'updated': latest_sync.records_updated,
            'failed': latest_sync.records_failed
        } 