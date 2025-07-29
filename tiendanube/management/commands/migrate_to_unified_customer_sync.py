from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from tiendanube.services.unified_customer_sync_service import UnifiedCustomerSyncService
from tiendanube.models_unified import TiendaNubeUnifiedConfig
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = _('Migra datos desde los sistemas antiguos de sincronización de clientes al sistema unificado')

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help=_('Forzar migración incluso si ya existen datos'),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=_('Simular migración sin guardar cambios'),
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(_('Iniciando migración al sistema unificado de sincronización de clientes...'))
        )
        
        # Verificar configuración
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config:
            self.stdout.write(
                self.style.ERROR(_('No hay configuración activa para sincronización unificada. Por favor, configure primero el sistema unificado.'))
            )
            return
        
        try:
            # Crear servicio
            service = UnifiedCustomerSyncService(config)
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING(_('Ejecutando en modo simulación (dry-run)...'))
                )
                # En modo dry-run, solo mostrar estadísticas
                self._show_migration_stats()
            else:
                # Ejecutar migración
                migrated_count, error_count = service.migrate_from_old_systems()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        _('Migración completada: {migrated} mapeos migrados, {errors} errores').format(
                            migrated=migrated_count,
                            errors=error_count
                        )
                    )
                )
                
                if error_count > 0:
                    self.stdout.write(
                        self.style.WARNING(_('Algunos mapeos no pudieron ser migrados. Revise los logs para más detalles.'))
                    )
                
                # Mostrar estadísticas finales
                self._show_final_stats()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(_('Error durante la migración: {error}').format(error=str(e)))
            )
            logger.error(f"Error en migración: {str(e)}")

    def _show_migration_stats(self):
        """Muestra estadísticas de migración."""
        from tiendanube.models_synap import TiendaNubeCustomerMapping
        from tiendanube.models_adminet import TiendaNubeClienteMap
        from tiendanube.models_unified import TiendaNubeUnifiedCustomerMapping
        
        # Contar mapeos existentes
        synap_mappings = TiendaNubeCustomerMapping.objects.count()
        adminet_mappings = TiendaNubeClienteMap.objects.count()
        unified_mappings = TiendaNubeUnifiedCustomerMapping.objects.count()
        
        self.stdout.write(_('Estadísticas de migración:'))
        self.stdout.write(f"  - Mapeos Synap-Tiendanube: {synap_mappings}")
        self.stdout.write(f"  - Mapeos AdministraNET-Tiendanube: {adminet_mappings}")
        self.stdout.write(f"  - Mapeos unificados existentes: {unified_mappings}")
        self.stdout.write(f"  - Total a migrar: {synap_mappings + adminet_mappings}")

    def _show_final_stats(self):
        """Muestra estadísticas finales después de la migración."""
        from tiendanube.models_unified import TiendaNubeUnifiedCustomerMapping
        
        total_mappings = TiendaNubeUnifiedCustomerMapping.objects.count()
        synced_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(sync_status='synced').count()
        pending_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(sync_status='pending').count()
        error_mappings = TiendaNubeUnifiedCustomerMapping.objects.filter(sync_status='error').count()
        
        self.stdout.write(_('Estadísticas finales:'))
        self.stdout.write(f"  - Total de mapeos unificados: {total_mappings}")
        self.stdout.write(f"  - Mapeos sincronizados: {synced_mappings}")
        self.stdout.write(f"  - Mapeos pendientes: {pending_mappings}")
        self.stdout.write(f"  - Mapeos con error: {error_mappings}")
        
        if total_mappings > 0:
            sync_percentage = (synced_mappings / total_mappings) * 100
            self.stdout.write(f"  - Porcentaje de sincronización: {sync_percentage:.1f}%") 