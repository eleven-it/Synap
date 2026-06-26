"""
Comando de gestión para migrar datos desde la app tiendanube a tiendanube_administranet.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Comando para migrar datos desde la app tiendanube a tiendanube_administranet.
    """
    
    help = 'Migra datos desde la app tiendanube a tiendanube_administranet'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar en modo simulación sin hacer cambios',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la migración incluso si hay errores',
        )
        parser.add_argument(
            '--skip-configs',
            action='store_true',
            help='Saltar migración de configuraciones',
        )
        parser.add_argument(
            '--skip-mappings',
            action='store_true',
            help='Saltar migración de mapeos',
        )
        parser.add_argument(
            '--skip-logs',
            action='store_true',
            help='Saltar migración de logs',
        )
    
    def handle(self, *args, **options):
        """Ejecutar la migración."""
        dry_run = options['dry_run']
        force = options['force']
        skip_configs = options['skip_configs']
        skip_mappings = options['skip_mappings']
        skip_logs = options['skip_logs']
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando migración a tiendanube_administranet...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  Ejecutando en modo simulación (dry-run)')
            )
        
        try:
            # Importar modelos de la nueva app
            from tiendanube_administranet.models import (
                TiendanubeConfig, AdministraNETConfig, CustomerMapping, SyncLog
            )
            
            # Importar modelos de la app anterior (si existen)
            try:
                from tiendanube.models import (
                    TiendanubeConfig as OldTiendanubeConfig,
                    TiendanubeAdminetConfig as OldAdminetConfig,
                    TiendanubeUnifiedCustomerMapping as OldCustomerMapping,
                    TiendanubeUnifiedSyncLog as OldSyncLog
                )
                old_models_exist = True
            except ImportError:
                self.stdout.write(
                    self.style.WARNING('⚠️  No se encontraron modelos de la app anterior')
                )
                old_models_exist = False
            
            if not old_models_exist and not force:
                raise CommandError(
                    'No se encontraron modelos de la app anterior. Use --force para continuar.'
                )
            
            # Estadísticas
            stats = {
                'configs_migrated': 0,
                'mappings_migrated': 0,
                'logs_migrated': 0,
                'errors': []
            }
            
            # Migrar configuraciones de Tiendanube
            if not skip_configs and old_models_exist:
                self.stdout.write('📋 Migrando configuraciones de Tiendanube...')
                stats['configs_migrated'] += self._migrate_tiendanube_configs(
                    OldTiendanubeConfig, TiendanubeConfig, dry_run
                )
            
            # Migrar configuraciones de AdministraNET
            if not skip_configs and old_models_exist:
                self.stdout.write('📋 Migrando configuraciones de AdministraNET...')
                stats['configs_migrated'] += self._migrate_adminet_configs(
                    OldAdminetConfig, AdministraNETConfig, dry_run
                )
            
            # Migrar mapeos de clientes
            if not skip_mappings and old_models_exist:
                self.stdout.write('👥 Migrando mapeos de clientes...')
                stats['mappings_migrated'] += self._migrate_customer_mappings(
                    OldCustomerMapping, CustomerMapping, dry_run
                )
            
            # Migrar logs de sincronización
            if not skip_logs and old_models_exist:
                self.stdout.write('📝 Migrando logs de sincronización...')
                stats['logs_migrated'] += self._migrate_sync_logs(
                    OldSyncLog, SyncLog, dry_run
                )
            
            # Mostrar resumen
            self._show_migration_summary(stats, dry_run)
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS('✅ Migración completada exitosamente!')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('✅ Simulación completada. Ejecute sin --dry-run para aplicar cambios.')
                )
                
        except Exception as e:
            logger.error(f"Error en migración: {str(e)}")
            if force:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error en migración: {str(e)}')
                )
            else:
                raise CommandError(f'Error en migración: {str(e)}')
    
    def _migrate_tiendanube_configs(self, old_model, new_model, dry_run):
        """Migrar configuraciones de Tiendanube."""
        migrated_count = 0
        
        try:
            old_configs = old_model.objects.all()
            
            for old_config in old_configs:
                try:
                    if not dry_run:
                        # Verificar si ya existe
                        existing = new_model.objects.filter(store_id=old_config.store_id).first()
                        if existing:
                            # Actualizar configuración existente
                            existing.name = old_config.name or f"Migrated {old_config.store_id}"
                            existing.access_token = old_config.access_token
                            existing.api_url = getattr(old_config, 'api_url', DEFAULT_TIENDANUBE_API_URL)
                            existing.is_active = old_config.is_active
                            existing.save()
                        else:
                            # Crear nueva configuración
                            new_model.objects.create(
                                name=old_config.name or f"Migrated {old_config.store_id}",
                                store_id=old_config.store_id,
                                access_token=old_config.access_token,
                                api_url=getattr(old_config, 'api_url', f'https://api.tiendanube.com/2025-03'),
                                is_active=old_config.is_active
                            )
                    
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error migrando configuración Tiendanube {old_config.id}: {str(e)}")
                    if not dry_run:
                        raise
                        
        except Exception as e:
            logger.error(f"Error migrando configuraciones de Tiendanube: {str(e)}")
            if not dry_run:
                raise
        
        return migrated_count
    
    def _migrate_adminet_configs(self, old_model, new_model, dry_run):
        """Migrar configuraciones de AdministraNET."""
        migrated_count = 0
        
        try:
            old_configs = old_model.objects.all()
            
            for old_config in old_configs:
                try:
                    if not dry_run:
                        # Verificar si ya existe
                        existing = new_model.objects.filter(database=old_config.database).first()

                        if existing:
                            existing.name = old_config.name or f"Migrated {old_config.database}"
                            existing.is_active = old_config.is_active
                            existing.save()
                        else:
                            new_model.objects.create(
                                name=old_config.name or f"Migrated {old_config.database}",
                                database=old_config.database,
                                is_active=old_config.is_active,
                            )
                    
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error migrando configuración AdministraNET {old_config.id}: {str(e)}")
                    if not dry_run:
                        raise
                        
        except Exception as e:
            logger.error(f"Error migrando configuraciones de AdministraNET: {str(e)}")
            if not dry_run:
                raise
        
        return migrated_count
    
    def _migrate_customer_mappings(self, old_model, new_model, dry_run):
        """Migrar mapeos de clientes."""
        migrated_count = 0
        
        try:
            old_mappings = old_model.objects.all()
            
            for old_mapping in old_mappings:
                try:
                    if not dry_run:
                        # Verificar si ya existe
                        existing = new_model.objects.filter(
                            tiendanube_email=old_mapping.tiendanube_email
                        ).first()
                        
                        if existing:
                            # Actualizar mapeo existente
                            existing.tiendanube_id = old_mapping.tiendanube_id
                            existing.tiendanube_name = old_mapping.tiendanube_name
                            existing.tiendanube_phone = old_mapping.tiendanube_phone
                            existing.adminet_codigo = old_mapping.adminet_codigo
                            existing.adminet_nombre = old_mapping.adminet_nombre
                            existing.adminet_documento = old_mapping.adminet_documento
                            existing.adminet_telefono = old_mapping.adminet_telefono
                            existing.sync_direction = old_mapping.sync_direction
                            existing.sync_status = old_mapping.sync_status
                            existing.sync_enabled = old_mapping.sync_enabled
                            existing.last_synced = old_mapping.last_synced
                            existing.error_message = old_mapping.error_message
                            existing.save()
                        else:
                            # Crear nuevo mapeo
                            new_model.objects.create(
                                tiendanube_id=old_mapping.tiendanube_id,
                                tiendanube_email=old_mapping.tiendanube_email,
                                tiendanube_name=old_mapping.tiendanube_name,
                                tiendanube_phone=old_mapping.tiendanube_phone,
                                adminet_codigo=old_mapping.adminet_codigo,
                                adminet_nombre=old_mapping.adminet_nombre,
                                adminet_documento=old_mapping.adminet_documento,
                                adminet_telefono=old_mapping.adminet_telefono,
                                sync_direction=old_mapping.sync_direction,
                                sync_status=old_mapping.sync_status,
                                sync_enabled=old_mapping.sync_enabled,
                                last_synced=old_mapping.last_synced,
                                error_message=old_mapping.error_message
                            )
                    
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error migrando mapeo {old_mapping.id}: {str(e)}")
                    if not dry_run:
                        raise
                        
        except Exception as e:
            logger.error(f"Error migrando mapeos de clientes: {str(e)}")
            if not dry_run:
                raise
        
        return migrated_count
    
    def _migrate_sync_logs(self, old_model, new_model, dry_run):
        """Migrar logs de sincronización."""
        migrated_count = 0
        
        try:
            old_logs = old_model.objects.all()
            
            for old_log in old_logs:
                try:
                    if not dry_run:
                        # Crear nuevo log
                        new_model.objects.create(
                            sync_type=old_log.sync_type,
                            status=old_log.status,
                            platform=old_log.platform,
                            mapping=None,  # Se puede relacionar después si es necesario
                            message=old_log.message,
                            details=old_log.details or {},
                            items_processed=old_log.items_processed,
                            items_success=old_log.items_success,
                            items_failed=old_log.items_failed,
                            started_at=old_log.started_at,
                            completed_at=old_log.completed_at
                        )
                    
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error migrando log {old_log.id}: {str(e)}")
                    if not dry_run:
                        raise
                        
        except Exception as e:
            logger.error(f"Error migrando logs de sincronización: {str(e)}")
            if not dry_run:
                raise
        
        return migrated_count
    
    def _show_migration_summary(self, stats, dry_run):
        """Mostrar resumen de la migración."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('📊 RESUMEN DE MIGRACIÓN')
        self.stdout.write('='*50)
        
        self.stdout.write(f"Configuraciones migradas: {stats['configs_migrated']}")
        self.stdout.write(f"Mapeos de clientes migrados: {stats['mappings_migrated']}")
        self.stdout.write(f"Logs migrados: {stats['logs_migrated']}")
        
        if stats['errors']:
            self.stdout.write(f"Errores encontrados: {len(stats['errors'])}")
            for error in stats['errors']:
                self.stdout.write(f"  - {error}")
        
        total_migrated = (
            stats['configs_migrated'] + 
            stats['mappings_migrated'] + 
            stats['logs_migrated']
        )
        
        self.stdout.write(f"\nTotal de registros procesados: {total_migrated}")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n⚠️  Este fue un modo simulación. Ejecute sin --dry-run para aplicar cambios.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Migración completada exitosamente!')
            ) 