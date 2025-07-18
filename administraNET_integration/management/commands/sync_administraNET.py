from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
from administraNET_integration.models import AdministraNETConfig, SyncLog
from administraNET_integration.services.sync_service import AdministraNETSyncService


class Command(BaseCommand):
    help = 'Sincronizar datos con administraNET'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['FULL', 'PRODUCTS', 'STOCK', 'CUSTOMERS', 'ORDERS'],
            default='FULL',
            help='Tipo de sincronización a ejecutar'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar sincronización incluso si no hay configuración activa'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar en modo simulación sin guardar cambios'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        sync_type = options['type']
        force = options['force']
        dry_run = options['dry_run']
        verbose = options['verbose']

        self.stdout.write(
            self.style.SUCCESS(f'🚀 Iniciando sincronización {sync_type} con administraNET')
        )

        # Verificar configuración
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config and not force:
                raise CommandError(
                    'No hay configuración activa de administraNET. '
                    'Use --force para continuar con la configuración por defecto.'
                )
            
            if not config:
                self.stdout.write(
                    self.style.WARNING('⚠️  No hay configuración activa, usando configuración por defecto')
                )
                # Crear configuración temporal para la prueba
                config = AdministraNETConfig(
                    host='localhost',
                    port=3306,
                    database_name='administraNET_dev',
                    username='root',
                    password='',
                    is_active=True
                )

        except Exception as e:
            raise CommandError(f'Error obteniendo configuración: {e}')

        # Crear log de sincronización
        try:
            sync_log = SyncLog.objects.create(
                sync_type=sync_type,
                status='RUNNING'
            )
            self.stdout.write(f'📝 Log de sincronización creado: {sync_log.id}')
        except Exception as e:
            raise CommandError(f'Error creando log de sincronización: {e}')

        # Ejecutar sincronización
        try:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('🔍 Ejecutando en modo simulación (dry-run)')
                )
                result = self._dry_run_sync(config, sync_type, verbose)
            else:
                sync_service = AdministraNETSyncService(config)
                
                if sync_type == 'FULL':
                    result = sync_service.sync_all(sync_log)
                else:
                    result = sync_service.sync_by_type(sync_type, sync_log)

            # Mostrar resultados
            self._display_results(result, verbose)

        except Exception as e:
            error_msg = f'Error durante la sincronización: {e}'
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            
            # Actualizar log con error
            try:
                sync_log.mark_completed(success=False, error_message=error_msg)
            except:
                pass
            
            raise CommandError(error_msg)

    def _dry_run_sync(self, config, sync_type, verbose):
        """
        Ejecutar sincronización en modo simulación
        """
        from administraNET_integration.services.connection_service import AdministraNETConnectionService
        
        self.stdout.write('🔍 Probando conexión...')
        
        connection_service = AdministraNETConnectionService(config)
        test_result = connection_service.test_connection(test_tables=True, test_queries=True)
        
        if not test_result['success']:
            return {
                'success': False,
                'error': f"Error de conexión: {test_result.get('error', 'Error desconocido')}"
            }
        
        self.stdout.write('✅ Conexión exitosa')
        
        if verbose:
            self.stdout.write(f"📊 Base de datos: {test_result['database_info']['name']}")
            self.stdout.write(f"📊 Total tablas: {test_result['database_info']['total_tables']}")
            self.stdout.write(f"📊 Tamaño: {test_result['database_info']['size_mb']} MB")
            
            for table, info in test_result['tables'].items():
                if info['exists']:
                    self.stdout.write(f"✅ {table}: {info['record_count']:,} registros")
                else:
                    self.stdout.write(f"❌ {table}: No encontrada")
        
        # Simular estadísticas
        return {
            'success': True,
            'processed': 100,
            'created': 25,
            'updated': 50,
            'failed': 5,
            'message': 'Simulación completada exitosamente'
        }

    def _display_results(self, result, verbose):
        """
        Mostrar resultados de la sincronización
        """
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS('✅ Sincronización completada exitosamente')
            )
            
            if verbose:
                self.stdout.write(f"📊 Registros procesados: {result.get('processed', 0):,}")
                self.stdout.write(f"📊 Registros creados: {result.get('created', 0):,}")
                self.stdout.write(f"📊 Registros actualizados: {result.get('updated', 0):,}")
                self.stdout.write(f"📊 Registros fallidos: {result.get('failed', 0):,}")
            
            if 'message' in result:
                self.stdout.write(f"💬 {result['message']}")
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Error en sincronización: {result.get('error', 'Error desconocido')}")
            ) 