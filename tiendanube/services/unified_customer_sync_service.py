import requests
import logging
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

from ..models_unified import (
    TiendaNubeUnifiedCustomerMapping, 
    TiendaNubeUnifiedSyncLog, 
    TiendaNubeUnifiedConfig
)
from ..models_synap import TiendaNubeCustomerMapping
from ..models_adminet import TiendaNubeClienteMap
from administraNET_integration.services.connection_service import AdministraNETConnectionService
from sales.models import Client
from core.models import Contact
from sales.models import SalesOrder

logger = logging.getLogger(__name__)

class UnifiedCustomerSyncService:
    """
    Servicio unificado para sincronización de clientes entre Synap, Tiendanube y AdministraNET.
    Combina toda la lógica de sincronización en un solo servicio.
    """
    
    def __init__(self, config: Optional[TiendaNubeUnifiedConfig] = None):
        self.config = config or TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not self.config:
            raise ValueError("No hay configuración activa para sincronización unificada")
        
        self.tiendanube_config = self.config.get_tiendanube_config()
        self.adminet_config = self.config.get_adminet_config()
        
        # Headers para API de Tiendanube
        self.tiendanube_headers = {
            'Content-Type': 'application/json',
            'Authentication': f'bearer {self.tiendanube_config["access_token"]}',
            'User-Agent': 'synap_tiendanube_unified - synap@administranet.com.ar'
        }
        
        # Servicio de conexión MySQL para AdministraNET
        if self.adminet_config and self.adminet_config.get('host'):
            # Crear configuración temporal para el servicio
            class TempAdminetConfig:
                def __init__(self, config_dict):
                    self.host = config_dict.get('host')
                    self.port = config_dict.get('port', 3306)
                    self.database_name = config_dict.get('database')
                    self.username = config_dict.get('user')
                    self.password = config_dict.get('password')
                
                def get_connection_string(self):
                    return f"{self.host}:{self.port}/{self.database_name}"
            
            temp_config = TempAdminetConfig(self.adminet_config)
            self.mysql_service = AdministraNETConnectionService(temp_config)
        else:
            self.mysql_service = None

    def get_sync_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de sincronización.
        """
        total_mappings = TiendaNubeUnifiedCustomerMapping.objects.count()
        synced_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(sync_status='synced').count()
        pending_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(sync_status='pending').count()
        error_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(sync_status='error').count()
        
        # Estadísticas por plataforma
        tiendanube_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(tiendanube_id__isnull=False).count()
        synap_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(synap_client__isnull=False).count()
        adminet_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(adminet_codigo__isnull=False).count()
        
        return {
            'total_mappings': total_mappings,
            'synced_mappings': synced_mappings,
            'pending_mappings': pending_mappings,
            'error_mappings': error_mappings,
            'tiendanube_mappings': tiendanube_mappings,
            'synap_mappings': synap_mappings,
            'adminet_mappings': adminet_mappings,
            'sync_percentage': (synced_mappings / total_mappings * 100) if total_mappings > 0 else 0
        }

    def migrate_from_old_systems(self) -> Tuple[int, int]:
        """
        Migra datos desde los sistemas antiguos (TiendaNubeCustomerMapping y TiendaNubeClienteMap).
        """
        migrated_count = 0
        error_count = 0
        
        try:
            # Migrar desde TiendaNubeCustomerMapping (Synap-Tiendanube)
            for old_mapping in TiendaNubeCustomerMapping.objects.all():
                try:
                    with transaction.atomic():
                        # Verificar si ya existe un mapeo unificado
                        existing = TiendaNubeUnifiedCustomerMapping.objects.filter(
                            tiendanube_id=old_mapping.tiendanube_id
                        ).first()
                        
                        if not existing:
                            # Crear nuevo mapeo unificado
                            unified_mapping = TiendaNubeUnifiedCustomerMapping.objects.create(
                                tiendanube_id=old_mapping.tiendanube_id,
                                tiendanube_email=old_mapping.tiendanube_email,
                                tiendanube_document=old_mapping.tiendanube_document,
                                synap_client=old_mapping.client,
                                sync_status=old_mapping.sync_status,
                                sync_enabled=old_mapping.sync_enabled,
                                sync_direction='bidirectional',
                                last_synced=old_mapping.last_synced
                            )
                            migrated_count += 1
                            logger.info(f"Migrado mapeo Synap-Tiendanube: {old_mapping.client.name}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error migrando mapeo Synap-Tiendanube: {str(e)}")
            
            # Migrar desde TiendaNubeClienteMap (AdministraNET-Tiendanube)
            for old_mapping in TiendaNubeClienteMap.objects.all():
                try:
                    with transaction.atomic():
                        # Verificar si ya existe un mapeo unificado
                        existing = TiendaNubeUnifiedCustomerMapping.objects.filter(
                            tiendanube_email=old_mapping.tiendanube_email
                        ).first()
                        
                        if existing:
                            # Actualizar mapeo existente con datos de AdministraNET
                            existing.adminet_codigo = old_mapping.adminet_codigo
                            existing.adminet_nombre = old_mapping.adminet_nombre
                            existing.adminet_documento = old_mapping.adminet_documento
                            existing.sync_direction = 'bidirectional'
                            existing.sync_enabled = old_mapping.activo
                            existing.save()
                            migrated_count += 1
                            logger.info(f"Actualizado mapeo con AdministraNET: {old_mapping.tiendanube_email}")
                        else:
                            # Crear nuevo mapeo unificado solo con AdministraNET
                            unified_mapping = TiendaNubeUnifiedCustomerMapping.objects.create(
                                tiendanube_email=old_mapping.tiendanube_email,
                                adminet_codigo=old_mapping.adminet_codigo,
                                adminet_nombre=old_mapping.adminet_nombre,
                                adminet_documento=old_mapping.adminet_documento,
                                sync_direction='adminet_only',
                                sync_status='synced' if old_mapping.activo else 'pending',
                                sync_enabled=old_mapping.activo
                            )
                            migrated_count += 1
                            logger.info(f"Migrado mapeo AdministraNET: {old_mapping.tiendanube_email}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error migrando mapeo AdministraNET: {str(e)}")
            
            self.log_sync('migration', 'success', f'Migrados {migrated_count} mapeos, {error_count} errores')
            
        except Exception as e:
            error_msg = f"Error en migración: {str(e)}"
            self.log_sync('migration', 'error', error_msg)
            logger.error(error_msg)
        
        return migrated_count, error_count

    def sync_customers_from_tiendanube(self, limit: int = 100, offset: int = 0) -> Tuple[int, int]:
        """
        Sincroniza clientes desde Tiendanube hacia Synap y AdministraNET.
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            # Obtener clientes de Tiendanube
            response = requests.get(
                f"{self.tiendanube_config['api_url']}/{self.tiendanube_config['store_id']}/customers",
                headers=self.tiendanube_headers,
                params={'limit': limit, 'offset': offset}
            )
            
            if response.status_code == 404:
                self.log_sync('customer_sync', 'info', "No hay clientes para sincronizar o endpoint no disponible")
                return 0, 0
            elif response.status_code != 200:
                self.log_sync('customer_sync', 'error', f"Error obteniendo clientes: {response.status_code}")
                return 0, 1
            
            customers_data = response.json()
            
            for customer_data in customers_data:
                try:
                    with transaction.atomic():
                        # Verificar si ya existe el mapping
                        if TiendaNubeUnifiedCustomerMapping.objects.filter(tiendanube_id=customer_data['id']).exists():
                            continue
                        
                        # Crear o actualizar cliente en Synap
                        synap_client, synap_contact = self._create_or_update_synap_customer(customer_data)
                        
                        # Buscar cliente en AdministraNET
                        adminet_codigo = self._find_adminet_customer(customer_data)
                        
                        # Crear mapping unificado
                        mapping = TiendaNubeUnifiedCustomerMapping.objects.create(
                            tiendanube_id=customer_data['id'],
                            tiendanube_email=customer_data.get('email', ''),
                            tiendanube_document=customer_data.get('document', ''),
                            synap_client=synap_client,
                            synap_contact=synap_contact,
                            adminet_codigo=adminet_codigo,
                            sync_status=TiendaNubeUnifiedCustomerMapping.SyncStatus.SYNCED
                        )
                        
                        self.log_sync('mapping_create', 'success', f'Cliente {customer_data.get("name", "N/A")} mapeado exitosamente', mapping=mapping)
                        success_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Error procesando cliente {customer_data.get('id', 'N/A')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Actualizar configuración
            self.config.last_sync = timezone.now()
            self.config.save(update_fields=['last_sync'])
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('customer_sync', status, f'Sincronizados desde Tiendanube: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            error_msg = f"Error general en sincronización desde Tiendanube: {str(e)}"
            self.log_sync('customer_sync', 'error', error_msg)
            logger.error(error_msg)
            return 0, 1
        
        return success_count, failed_count

    def sync_customers_to_tiendanube(self, limit: int = 100, offset: int = 0) -> Tuple[int, int]:
        """
        Sincroniza clientes desde Synap hacia Tiendanube.
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            # Obtener clientes de Synap con tag tiendanube
            contacts_with_tiendanube = Contact.objects.filter(
                tags__icontains='tiendanube',
                is_active=True
            )
            
            # Obtener clientes relacionados
            client_ids = set()
            for contact in contacts_with_tiendanube:
                for relationship in contact.relationships.filter(
                    content_type__model='client',
                    is_active=True
                ):
                    client_ids.add(relationship.object_id)
            
            # Sincronizar clientes
            clients = Client.objects.filter(id__in=list(client_ids)[offset:offset+limit])
            
            for client in clients:
                try:
                    success, message = self._sync_single_customer_to_tiendanube(client)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Error sincronizando {client.name}: {message}")
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error procesando {client.name}: {str(e)}")
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('customer_sync', status, f'Sincronizados hacia Tiendanube: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            error_msg = f"Error general en sincronización hacia Tiendanube: {str(e)}"
            self.log_sync('customer_sync', 'error', error_msg)
            logger.error(error_msg)
            return 0, 1
        
        return success_count, failed_count

    def sync_customers_with_adminet(self, limit: int = 100, offset: int = 0) -> Tuple[int, int]:
        """
        Sincroniza clientes con AdministraNET.
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        if not self.mysql_service:
            error_msg = "No hay conexión configurada con AdministraNET"
            self.log_sync('adminet_sync', 'error', error_msg)
            return 0, 1
        
        try:
            # Obtener clientes de AdministraNET
            query = """
                SELECT Codigo as codigo, nombre_cliente as nombre, Email as email, CUIT as cuit
                FROM cliente 
                WHERE Estado = 'Activo'
                ORDER BY nombre_cliente
                LIMIT %s OFFSET %s
            """
            
            result = self.mysql_service.execute_query(query, (limit, offset))
            
            if not result.get('success'):
                error_msg = f"Error obteniendo clientes de AdministraNET: {result.get('error', 'Error desconocido')}"
                self.log_sync('adminet_sync', 'error', error_msg)
                return 0, 1
            
            clientes = result.get('data', [])
            logger.info(f"Obtenidos {len(clientes)} clientes de AdministraNET")
            
            for cliente in clientes:
                try:
                    with transaction.atomic():
                        # Buscar mapping existente por código de AdministraNET
                        mapping = TiendaNubeUnifiedCustomerMapping.objects.filter(
                            adminet_codigo=cliente['codigo']
                        ).first()
                        
                        # Generar email único para clientes sin email
                        email = cliente.get('email', '').strip()
                        if not email:
                            email = f"adminet_{cliente['codigo']}@administranet.local"
                        
                        if mapping:
                            # Actualizar información de AdministraNET
                            mapping.adminet_nombre = cliente['nombre']
                            mapping.adminet_documento = cliente.get('cuit', '')
                            mapping.sync_status = 'synced'
                            mapping.last_synced = timezone.now()
                            mapping.save(update_fields=['adminet_nombre', 'adminet_documento', 'sync_status', 'last_synced'])
                            logger.info(f"Actualizado mapping para cliente AdministraNET {cliente['codigo']}")
                        else:
                            # Verificar si ya existe un mapping con este email
                            existing_email_mapping = TiendaNubeUnifiedCustomerMapping.objects.filter(
                                tiendanube_email=email
                            ).first()
                            
                            if existing_email_mapping:
                                # Si existe, actualizar con el código de AdministraNET
                                existing_email_mapping.adminet_codigo = cliente['codigo']
                                existing_email_mapping.adminet_nombre = cliente['nombre']
                                existing_email_mapping.adminet_documento = cliente.get('cuit', '')
                                existing_email_mapping.sync_direction = 'bidirectional'
                                existing_email_mapping.sync_status = 'synced'
                                existing_email_mapping.last_synced = timezone.now()
                                existing_email_mapping.save()
                                logger.info(f"Actualizado mapping existente con código AdministraNET {cliente['codigo']}")
                            else:
                                # Crear nuevo mapping
                                mapping = TiendaNubeUnifiedCustomerMapping.objects.create(
                                    tiendanube_email=email,
                                    adminet_codigo=cliente['codigo'],
                                    adminet_nombre=cliente['nombre'],
                                    adminet_documento=cliente.get('cuit', ''),
                                    sync_direction='adminet_only',
                                    sync_status='synced',
                                    sync_enabled=True,
                                    last_synced=timezone.now()
                                )
                                logger.info(f"Creado nuevo mapping para cliente AdministraNET {cliente['codigo']}")
                        
                        success_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Error procesando cliente AdministraNET {cliente['codigo']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('adminet_sync', status, f'Sincronizados con AdministraNET: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            error_msg = f"Error general en sincronización con AdministraNET: {str(e)}"
            self.log_sync('adminet_sync', 'error', error_msg)
            logger.error(error_msg)
            return 0, 1
        
        return success_count, failed_count
    
    def create_customer_mapping(self, tiendanube_email: str, adminet_codigo: int, 
                              sync_direction: str = 'bidirectional') -> Optional[TiendaNubeUnifiedCustomerMapping]:
        """
        Crea un mapeo manual entre cliente de Tiendanube y AdministraNET.
        """
        try:
            with transaction.atomic():
                # Verificar que no exista ya el mapeo
                if TiendaNubeUnifiedCustomerMapping.objects.filter(tiendanube_email=tiendanube_email).exists():
                    raise ValueError(f"Ya existe un mapeo para el email {tiendanube_email}")
                
                if TiendaNubeUnifiedCustomerMapping.objects.filter(adminet_codigo=adminet_codigo).exists():
                    raise ValueError(f"Ya existe un mapeo para el código AdministraNET {adminet_codigo}")
                
                # Obtener información del cliente de AdministraNET
                adminet_info = self._get_adminet_customer_info(adminet_codigo)
                
                # Crear mapping
                mapping = TiendaNubeUnifiedCustomerMapping.objects.create(
                    tiendanube_email=tiendanube_email,
                    adminet_codigo=adminet_codigo,
                    adminet_nombre=adminet_info.get('nombre_cliente', ''),
                    adminet_documento=adminet_info.get('cuit', ''),
                    sync_direction=sync_direction,
                    sync_status=TiendaNubeUnifiedCustomerMapping.SyncStatus.SYNCED
                )
                
                self.log_sync('mapping_create', 'success', f'Mapeo creado: {tiendanube_email} → {adminet_codigo}', mapping=mapping)
                return mapping
                
        except Exception as e:
            logger.error(f"Error creando mapeo: {str(e)}")
            raise

    def update_customer_mapping(self, mapping_id: int, **kwargs) -> Optional[TiendaNubeUnifiedCustomerMapping]:
        """
        Actualiza un mapeo de cliente existente.
        """
        try:
            mapping = TiendaNubeUnifiedCustomerMapping.objects.get(id=mapping_id)
            
            for field, value in kwargs.items():
                if hasattr(mapping, field):
                    setattr(mapping, field, value)
            
            mapping.save()
            self.log_sync('mapping_update', 'success', f'Mapeo actualizado: {mapping_id}')
            return mapping
            
        except TiendaNubeUnifiedCustomerMapping.DoesNotExist:
            raise ValueError(f"No se encontró el mapeo con ID {mapping_id}")
        except Exception as e:
            logger.error(f"Error actualizando mapeo: {str(e)}")
            raise

    def delete_customer_mapping(self, mapping_id: int) -> bool:
        """
        Elimina un mapeo de cliente.
        """
        try:
            mapping = TiendaNubeUnifiedCustomerMapping.objects.get(id=mapping_id)
            mapping.delete()
            self.log_sync('mapping_delete', 'success', f'Mapeo eliminado: {mapping_id}')
            return True
            
        except TiendaNubeUnifiedCustomerMapping.DoesNotExist:
            raise ValueError(f"No se encontró el mapeo con ID {mapping_id}")
        except Exception as e:
            logger.error(f"Error eliminando mapeo: {str(e)}")
            raise

    def _create_or_update_synap_customer(self, customer_data: Dict) -> Tuple[Optional[Client], Optional[Contact]]:
        """
        Crea o actualiza un cliente en Synap desde datos de Tiendanube.
        """
        email = customer_data.get('email', '').strip().lower()
        document = customer_data.get('document', '').strip()
        name = customer_data.get('name', '').strip() or customer_data.get('full_name', '').strip()
        
        # Buscar cliente existente por email
        synap_client = None
        if email:
            try:
                synap_client = Client.objects.get(email=email)
            except Client.DoesNotExist:
                pass
        
        # Si no existe, crear nuevo cliente
        if not synap_client:
            synap_client = Client.objects.create(
                name=name or 'Cliente Tiendanube',
                email=email,
                document_number=document,
                type='individual' if not document else 'company',
                credit_limit=Decimal('0.00')
            )
        
        # Crear o actualizar contacto
        synap_contact = None
        if email:
            synap_contact = Contact.objects.filter(email=email).first()
        
        if not synap_contact and document:
            synap_contact = Contact.objects.filter(notes__icontains=document).first()
        
        if not synap_contact:
            synap_contact = Contact.objects.create(
                name=name or 'Cliente Tiendanube',
                email=email,
                phone=customer_data.get('phone', ''),
                address=customer_data.get('address', ''),
                city=customer_data.get('city', ''),
                state=customer_data.get('state', ''),
                country=customer_data.get('country', 'Argentina'),
                notes=document,
                tags='tiendanube'
            )
        else:
            # Agregar tag tiendanube si no existe
            if 'tiendanube' not in (synap_contact.tags or '').lower():
                current_tags = synap_contact.tags or ''
                synap_contact.tags = f"{current_tags},tiendanube".strip(',')
                synap_contact.save()
        
        # Vincular como contacto primario si no existe relación
        if not synap_client.has_contact(synap_contact, relationship_type='primary'):
            synap_client.add_contact_relationship(synap_contact, relationship_type='primary')
        
        return synap_client, synap_contact

    def _get_adminet_customers(self) -> List[Dict[str, Any]]:
        """
        Obtiene clientes de AdministraNET.
        """
        try:
            if not self.mysql_service:
                logger.error("No hay servicio MySQL configurado")
                return []

            query = """
                SELECT 
                    Codigo as codigo,
                    nombre_cliente as nombre,
                    CUIT as documento,
                    Email as email,
                    telefono,
                    CONCAT(Calle, ' ', NroCalle, ' ', COALESCE(Dpto, '')) as direccion,
                    Estado as activo,
                    FechaAlta as fecha_alta
                FROM cliente 
                WHERE Estado = 'Activo'
                ORDER BY nombre_cliente
                LIMIT 100
            """
            
            result = self.mysql_service.execute_query(query)
            if result['success']:
                return result['data']
            else:
                logger.error(f"Error obteniendo clientes de AdministraNET: {result['error']}")
                return []
                
        except Exception as e:
            logger.error(f"Error en _get_adminet_customers: {str(e)}")
            return []

    def _find_adminet_customer(self, email: str = None, document: str = None) -> Optional[Dict[str, Any]]:
        """
        Busca un cliente en AdministraNET por email o documento.
        """
        try:
            if not self.mysql_service:
                logger.error("No hay servicio MySQL configurado")
                return None
            
            if not email and not document:
                return None
            
            # Construir consulta según los parámetros disponibles
            if email and document:
                query = """
                    SELECT 
                        Codigo as codigo,
                        nombre_cliente as nombre,
                        CUIT as documento,
                        Email as email,
                        telefono,
                        CONCAT(Calle, ' ', NroCalle, ' ', COALESCE(Dpto, '')) as direccion,
                        Estado as activo,
                        FechaAlta as fecha_alta
                    FROM cliente 
                    WHERE (Email = %s OR CUIT = %s) AND Estado = 'Activo'
                    LIMIT 1
                """
                params = (email.lower(), document)
            elif email:
                query = """
                    SELECT 
                        Codigo as codigo,
                        nombre_cliente as nombre,
                        CUIT as documento,
                        Email as email,
                        telefono,
                        CONCAT(Calle, ' ', NroCalle, ' ', COALESCE(Dpto, '')) as direccion,
                        Estado as activo,
                        FechaAlta as fecha_alta
                    FROM cliente 
                    WHERE Email = %s AND Estado = 'Activo'
                    LIMIT 1
                """
                params = (email.lower(),)
            else:  # document only
                query = """
                    SELECT 
                        Codigo as codigo,
                        nombre_cliente as nombre,
                        CUIT as documento,
                        Email as email,
                        telefono,
                        CONCAT(Calle, ' ', NroCalle, ' ', COALESCE(Dpto, '')) as direccion,
                        Estado as activo,
                        FechaAlta as fecha_alta
                    FROM cliente 
                    WHERE CUIT = %s AND Estado = 'Activo'
                    LIMIT 1
                """
                params = (document,)
            
            result = self.mysql_service.execute_query(query, params)
            if result['success'] and result['data']:
                return result['data'][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error en _find_adminet_customer: {str(e)}")
            return None

    def _get_adminet_customer_info(self, codigo: int) -> Dict[str, str]:
        """
        Obtiene información de un cliente de AdministraNET.
        """
        if not self.mysql_service:
            return {}
        
        try:
            query = """
                SELECT nombre_cliente, email, cuit
                FROM cliente
                WHERE codigo = %s
                LIMIT 1
            """
            result = self.mysql_service.execute_query(query, (codigo,), fetch_one=True)
            
            if result:
                return {
                    'nombre_cliente': result.get('nombre_cliente', ''),
                    'email': result.get('email', ''),
                    'cuit': result.get('cuit', '')
                }
            
        except Exception as e:
            logger.error(f"Error obteniendo información de cliente AdministraNET: {str(e)}")
        
        return {}

    def _sync_single_customer_to_tiendanube(self, client: Client) -> Tuple[bool, str]:
        """
        Sincroniza un cliente individual hacia Tiendanube.
        """
        try:
            # Verificar que el cliente tenga tag tiendanube
            primary_contact = client.get_primary_contact_object()
            if not primary_contact or 'tiendanube' not in (primary_contact.tags or '').lower():
                return True, "Cliente no marcado para sincronización con Tiendanube"
            
            # Verificar si ya existe mapping
            mapping, created = TiendaNubeUnifiedCustomerMapping.objects.get_or_create(
                synap_client=client,
                defaults={'sync_status': TiendaNubeUnifiedCustomerMapping.SyncStatus.PENDING}
            )
            
            if not created and mapping.sync_status == TiendaNubeUnifiedCustomerMapping.SyncStatus.SYNCED:
                return True, "Cliente ya sincronizado"
            
            # Obtener datos del cliente
            if primary_contact:
                customer_data = {
                    'name': primary_contact.display_name,
                    'email': primary_contact.email or client.email,
                    'document': primary_contact.notes or client.document_number or '',
                    'phone': primary_contact.phone or client.phone or '',
                    'address': primary_contact.full_address or client.get_full_address() or '',
                }
            else:
                customer_data = {
                    'name': client.name,
                    'email': client.email,
                    'document': client.document_number or '',
                    'phone': client.phone or '',
                    'address': client.get_full_address() or '',
                }
            
            if created:
                # Crear nuevo cliente en Tiendanube
                response = requests.post(
                    f"{self.tiendanube_config['api_url']}/{self.tiendanube_config['store_id']}/customers", 
                    headers=self.tiendanube_headers, 
                    json=customer_data
                )
            else:
                # Actualizar cliente existente
                response = requests.put(
                    f"{self.tiendanube_config['api_url']}/{self.tiendanube_config['store_id']}/customers/{mapping.tiendanube_id}", 
                    headers=self.tiendanube_headers, 
                    json=customer_data
                )
            
            if response.status_code == 404:
                mapping.update_sync_status(
                    TiendaNubeUnifiedCustomerMapping.SyncStatus.ERROR,
                    "Endpoint de clientes no disponible"
                )
                return True, "Endpoint de clientes no disponible"
            elif response.status_code in [200, 201]:
                customer_response = response.json()
                mapping.tiendanube_id = customer_response['id']
                mapping.tiendanube_email = customer_data['email']
                mapping.tiendanube_document = customer_data['document']
                mapping.update_sync_status(TiendaNubeUnifiedCustomerMapping.SyncStatus.SYNCED)
                return True, "Cliente sincronizado exitosamente"
            else:
                mapping.update_sync_status(
                    TiendaNubeUnifiedCustomerMapping.SyncStatus.ERROR,
                    f"Error {response.status_code}: {response.text}"
                )
                return False, f"Error {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)

    def log_sync(self, sync_type: str, status: str, message: str, 
                details: Optional[Dict] = None, mapping: Optional[TiendaNubeUnifiedCustomerMapping] = None):
        """
        Registra un log de sincronización.
        """
        try:
            TiendaNubeUnifiedSyncLog.objects.create(
                sync_type=sync_type,
                status=status,
                message=message,
                details=details or {},
                mapping=mapping,
                started_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error registrando log de sincronización: {str(e)}") 