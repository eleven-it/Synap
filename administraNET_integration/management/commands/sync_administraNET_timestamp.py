from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from administraNET_integration.models import AdministraNETConfig, SyncLog, SyncTimestampConfig
from administraNET_integration.services.timestamp_based_sync_service import TimestampBasedBidirectionalSyncService


class Command(BaseCommand):
    help = 'Sincronización bidireccional con resolución de conflictos basada en timestamps'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['PRODUCTS', 'CUSTOMERS', 'STOCK', 'ORDERS', 'ALL'],
            default='ALL',
            help=_('Tipo de sincronización a realizar')
        )
        parser.add_argument(
            '--direction',
            type=str,
            choices=['TO_SYNAP', 'FROM_SYNAP', 'BOTH'],
            default='BOTH',
            help=_('Dirección de sincronización')
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=_('Ejecutar en modo simulación sin realizar cambios')
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help=_('Forzar sincronización incluso si hay errores')
        )
        parser.add_argument(
            '--show-conflicts',
            action='store_true',
            help=_('Mostrar resumen de conflictos al final')
        )

    def handle(self, *args, **options):
        sync_type = options['type']
        direction = options['direction']
        dry_run = options['dry_run']
        force = options['force']
        show_conflicts = options['show_conflicts']

        self.stdout.write(
            self.style.SUCCESS(f'🚀 Iniciando sincronización con timestamps {sync_type} - {direction}')
        )

        # Verificar configuración
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            raise CommandError(_('No hay configuración activa de administraNET'))

        # Crear servicio de sincronización con timestamps
        sync_service = TimestampBasedBidirectionalSyncService(config)

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 Ejecutando en modo simulación (dry-run)')
            )
            self._dry_run_sync(sync_service, sync_type, direction)
            return

        # Realizar sincronización
        if sync_type == 'ALL':
            self._sync_all_types(sync_service, direction, force, show_conflicts)
        else:
            self._sync_single_type(sync_service, sync_type, direction, force, show_conflicts)

    def _sync_all_types(self, sync_service, direction, force, show_conflicts):
        """Sincronizar todos los tipos"""
        sync_types = ['PRODUCTS', 'CUSTOMERS', 'STOCK', 'ORDERS']
        
        total_results = {
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_failed': 0,
            'total_conflicts': 0,
            'errors': []
        }

        for sync_type in sync_types:
            self.stdout.write(f'\n📋 Sincronizando {sync_type}...')
            
            try:
                result = sync_service.sync_bidirectional(sync_type, direction)
                
                if result['success']:
                    total_results['total_processed'] += result['total_processed']
                    total_results['total_created'] += result['total_created']
                    total_results['total_updated'] += result['total_updated']
                    total_results['total_failed'] += result['total_failed']
                    total_results['total_conflicts'] += result.get('total_conflicts_resolved', 0)
                    
                    self._print_sync_results(result, sync_type)
                    
                    # Mostrar conflictos si se solicita
                    if show_conflicts and result.get('total_conflicts_resolved', 0) > 0:
                        self._show_conflict_summary(sync_service, result.get('sync_log'))
                else:
                    error_msg = f"Error en {sync_type}: {result.get('error', 'Error desconocido')}"
                    total_results['errors'].append(error_msg)
                    
                    if force:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  {error_msg} (continuando por --force)')
                        )
                    else:
                        raise CommandError(error_msg)
                        
            except Exception as e:
                error_msg = f"Error inesperado en {sync_type}: {str(e)}"
                total_results['errors'].append(error_msg)
                
                if force:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  {error_msg} (continuando por --force)')
                    )
                else:
                    raise CommandError(error_msg)

        # Mostrar resumen final
        self._print_final_summary(total_results)

    def _sync_single_type(self, sync_service, sync_type, direction, force, show_conflicts):
        """Sincronizar un tipo específico"""
        self.stdout.write(f'📋 Sincronizando {sync_type}...')
        
        try:
            result = sync_service.sync_bidirectional(sync_type, direction)
            
            if result['success']:
                self._print_sync_results(result, sync_type)
                
                # Mostrar conflictos si se solicita
                if show_conflicts and result.get('total_conflicts_resolved', 0) > 0:
                    self._show_conflict_summary(sync_service, result.get('sync_log'))
            else:
                error_msg = f"Error en {sync_type}: {result.get('error', 'Error desconocido')}"
                if force:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  {error_msg} (continuando por --force)')
                    )
                else:
                    raise CommandError(error_msg)
                    
        except Exception as e:
            error_msg = f"Error inesperado en {sync_type}: {str(e)}"
            if force:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {error_msg} (continuando por --force)')
                )
            else:
                raise CommandError(error_msg)

    def _print_sync_results(self, result, sync_type):
        """Imprimir resultados de sincronización"""
        self.stdout.write(
            self.style.SUCCESS(f'✅ {sync_type} completado:')
        )
        self.stdout.write(f'   📊 Procesados: {result["total_processed"]}')
        self.stdout.write(f'   ➕ Creados: {result["total_created"]}')
        self.stdout.write(f'   🔄 Actualizados: {result["total_updated"]}')
        self.stdout.write(f'   ❌ Fallidos: {result["total_failed"]}')
        
        if result.get('total_conflicts_resolved', 0) > 0:
            self.stdout.write(
                self.style.WARNING(f'   ⚠️  Conflictos resueltos: {result["total_conflicts_resolved"]}')
            )

    def _show_conflict_summary(self, sync_service, sync_log):
        """Mostrar resumen de conflictos"""
        if not sync_log:
            return
            
        summary = sync_service.get_conflict_summary(sync_log)
        
        self.stdout.write('\n🔍 Resumen de Conflictos:')
        self.stdout.write(f'   📊 Total de conflictos: {summary["total_conflicts"]}')
        self.stdout.write(f'   🏆 Synap ganó: {summary["synap_wins"]}')
        self.stdout.write(f'   🏆 administraNET ganó: {summary["adminet_wins"]}')
        self.stdout.write(f'   ⏸️  Sin cambios: {summary["no_change"]}')
        
        if summary['conflicts_by_type']:
            self.stdout.write('\n   📋 Por tipo de registro:')
            for record_type, stats in summary['conflicts_by_type'].items():
                self.stdout.write(f'      {record_type}: {stats["total"]} conflictos')
                self.stdout.write(f'        - Synap ganó: {stats["synap_wins"]}')
                self.stdout.write(f'        - administraNET ganó: {stats["adminet_wins"]}')

    def _print_final_summary(self, total_results):
        """Imprimir resumen final"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('🎉 Sincronización Completada'))
        self.stdout.write('='*50)
        self.stdout.write(f'📊 Total procesados: {total_results["total_processed"]}')
        self.stdout.write(f'➕ Total creados: {total_results["total_created"]}')
        self.stdout.write(f'🔄 Total actualizados: {total_results["total_updated"]}')
        self.stdout.write(f'❌ Total fallidos: {total_results["total_failed"]}')
        self.stdout.write(f'⚠️  Total conflictos resueltos: {total_results["total_conflicts"]}')
        
        if total_results['errors']:
            self.stdout.write('\n❌ Errores encontrados:')
            for error in total_results['errors']:
                self.stdout.write(f'   - {error}')

    def _dry_run_sync(self, sync_service, sync_type, direction):
        """Ejecutar sincronización en modo simulación"""
        self.stdout.write(
            self.style.WARNING('🔍 Modo simulación - No se realizarán cambios reales')
        )
        
        # Aquí podrías implementar la lógica de simulación
        # Por ahora solo mostrar información
        self.stdout.write(f'📋 Simulando sincronización {sync_type} - {direction}')
        self.stdout.write('   ✅ Verificaría conflictos de timestamp')
        self.stdout.write('   ✅ Aplicaría resolución basada en timestamps')
        self.stdout.write('   ✅ Registraría conflictos en logs')
        self.stdout.write('   ✅ Actualizaría campos de control de sincronización') 