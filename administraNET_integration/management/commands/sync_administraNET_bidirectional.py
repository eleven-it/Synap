from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from administraNET_integration.models import AdministraNETConfig, SyncLog
from administraNET_integration.services.bidirectional_sync_service import BidirectionalSyncService


class Command(BaseCommand):
    help = 'Sincronización bidireccional entre administraNET y Synap'

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

    def handle(self, *args, **options):
        sync_type = options['type']
        direction = options['direction']
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(f'🚀 Iniciando sincronización bidireccional {sync_type} - {direction}')
        )

        # Verificar configuración
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            raise CommandError(_('No hay configuración activa de administraNET'))

        # Crear servicio de sincronización
        sync_service = BidirectionalSyncService(config)

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 Ejecutando en modo simulación (dry-run)')
            )
            self._dry_run_sync(sync_service, sync_type, direction)
            return

        # Realizar sincronización
        if sync_type == 'ALL':
            self._sync_all_types(sync_service, direction, force)
        else:
            self._sync_single_type(sync_service, sync_type, direction, force)

    def _sync_all_types(self, sync_service, direction, force):
        """Sincronizar todos los tipos"""
        sync_types = ['PRODUCTS', 'CUSTOMERS', 'STOCK', 'ORDERS']
        
        total_results = {
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_failed': 0,
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
                    
                    self._print_sync_results(result, sync_type)
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

    def _sync_single_type(self, sync_service, sync_type, direction, force):
        """Sincronizar un tipo específico"""
        self.stdout.write(f'📋 Sincronizando {sync_type}...')
        
        try:
            result = sync_service.sync_bidirectional(sync_type, direction)
            
            if result['success']:
                self._print_sync_results(result, sync_type)
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

    def _dry_run_sync(self, sync_service, sync_type, direction):
        """Ejecutar sincronización en modo simulación"""
        self.stdout.write('🔍 Probando conexión...')
        
        try:
            # Verificar conexión
            config = sync_service.config
            connection = sync_service.connection_service.get_connection()
            
            if connection:
                self.stdout.write(
                    self.style.SUCCESS('✅ Conexión exitosa')
                )
                
                # Mostrar información de configuración
                self.stdout.write(f'\n📋 Configuración:')
                self.stdout.write(f'   Host: {config.host}')
                self.stdout.write(f'   Base de datos: {config.database_name}')
                self.stdout.write(f'   Usuario: {config.username}')
                self.stdout.write(f'   Intervalo de sync: {config.sync_interval} minutos')
                
                # Mostrar mapeos activos
                from administraNET_integration.models import TableMapping
                mappings = TableMapping.objects.filter(is_active=True)
                
                self.stdout.write(f'\n📋 Mapeos activos:')
                for mapping in mappings:
                    self.stdout.write(f'   {mapping.mapping_type}: {mapping.administraNET_table} → {mapping.synap_model}')
                    self.stdout.write(f'     Dirección: {mapping.sync_direction}')
                    self.stdout.write(f'     Campos: {len(mapping.field_mappings)} mapeados')
                
                # Mostrar estado de sincronización
                self.stdout.write(f'\n📋 Estado de sincronización:')
                for sync_type in ['PRODUCTS', 'CUSTOMERS', 'STOCK', 'ORDERS']:
                    status = sync_service.get_sync_status(sync_type)
                    self.stdout.write(f'   {sync_type}: {status["status"]} (última: {status["last_sync"]})')
                
                self.stdout.write(
                    self.style.SUCCESS('\n✅ Simulación completada exitosamente')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Error de conexión')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en simulación: {str(e)}')
            )

    def _print_sync_results(self, result, sync_type):
        """Imprimir resultados de sincronización"""
        self.stdout.write(f'\n📊 Resultados de {sync_type}:')
        
        if 'results' in result:
            # Resultados bidireccionales
            to_synap = result['results']['to_synap']
            from_synap = result['results']['from_synap']
            
            if to_synap['success']:
                self.stdout.write(f'   → Synap: {to_synap["processed"]} procesados, '
                                f'{to_synap["created"]} creados, {to_synap["updated"]} actualizados, '
                                f'{to_synap["failed"]} fallidos')
            
            if from_synap['success']:
                self.stdout.write(f'   ← administraNET: {from_synap["processed"]} procesados, '
                                f'{from_synap["created"]} creados, {from_synap["updated"]} actualizados, '
                                f'{from_synap["failed"]} fallidos')
        else:
            # Resultados unidireccionales
            self.stdout.write(f'   Procesados: {result["total_processed"]}')
            self.stdout.write(f'   Creados: {result["total_created"]}')
            self.stdout.write(f'   Actualizados: {result["total_updated"]}')
            self.stdout.write(f'   Fallidos: {result["total_failed"]}')

    def _print_final_summary(self, total_results):
        """Imprimir resumen final"""
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Sincronización completada')
        )
        
        self.stdout.write(f'\n📊 Resumen total:')
        self.stdout.write(f'   Procesados: {total_results["total_processed"]}')
        self.stdout.write(f'   Creados: {total_results["total_created"]}')
        self.stdout.write(f'   Actualizados: {total_results["total_updated"]}')
        self.stdout.write(f'   Fallidos: {total_results["total_failed"]}')
        
        if total_results['errors']:
            self.stdout.write(f'\n⚠️  Errores encontrados:')
            for error in total_results['errors']:
                self.stdout.write(f'   - {error}')
        
        # Calcular tasa de éxito
        total_processed = total_results['total_processed']
        successful = total_results['total_created'] + total_results['total_updated']
        
        if total_processed > 0:
            success_rate = (successful / total_processed) * 100
            self.stdout.write(f'\n📈 Tasa de éxito: {success_rate:.2f}%')
        
        if not total_results['errors']:
            self.stdout.write(
                self.style.SUCCESS('\n✅ Sincronización exitosa sin errores')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠️  Sincronización completada con errores')
            ) 