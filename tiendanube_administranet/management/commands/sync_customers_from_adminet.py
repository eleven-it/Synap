from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from tiendanube_administranet.models import AdministraNETConfig
from tiendanube_administranet.services.customer_sync_service import CustomerSyncService


class Command(BaseCommand):
    help = 'Sincroniza clientes desde AdministraNET hacia Synap'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Número máximo de clientes a sincronizar (default: 100)'
        )
        parser.add_argument(
            '--offset',
            type=int,
            default=0,
            help='Desplazamiento para paginación (default: 0)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar sincronización incluso si ya existen mapeos'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        offset = options['offset']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(
                f'🔄 Iniciando sincronización de clientes desde AdministraNET...'
            )
        )
        self.stdout.write(f'   📊 Límite: {limit} clientes')
        self.stdout.write(f'   📊 Offset: {offset}')
        self.stdout.write(f'   📊 Forzar: {"Sí" if force else "No"}')

        try:
            # Obtener configuración de AdministraNET
            adminet_config = AdministraNETConfig.objects.first()
            if not adminet_config:
                raise CommandError('❌ No hay configuración de AdministraNET. Configure primero la conexión.')

            self.stdout.write(f'✅ Configuración encontrada (esquema MySQL): {adminet_config.database}')

            # Crear servicio de sincronización
            sync_service = CustomerSyncService(adminet_config)

            # Ejecutar sincronización
            result = sync_service.sync_customers_from_adminet(limit=limit, offset=offset)

            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Sincronización completada exitosamente!'
                    )
                )
                self.stdout.write(f'   📈 Total procesados: {result["total_processed"]}')
                self.stdout.write(f'   ✅ Exitosos: {result["successful"]}')
                self.stdout.write(f'   ❌ Fallidos: {result["failed"]}')
                
                if 'sync_log_id' in result:
                    self.stdout.write(f'   📋 Log ID: {result["sync_log_id"]}')
                
                # Mostrar estadísticas actuales
                self._show_current_stats(sync_service)
                
            else:
                raise CommandError(f'❌ Error en sincronización: {result["message"]}')

        except Exception as e:
            raise CommandError(f'❌ Error ejecutando sincronización: {str(e)}')

    def _show_current_stats(self, sync_service):
        """Muestra estadísticas actuales de clientes."""
        try:
            # Obtener estadísticas de datos reales
            real_customers = sync_service.get_customers_with_adminet_data(limit=1000)
            fake_customers = sync_service.get_customers_with_fake_data(limit=1000)
            
            self.stdout.write('\n📊 ESTADÍSTICAS ACTUALES:')
            self.stdout.write(f'   🔵 Clientes con datos reales: {real_customers.get("total", 0)}')
            self.stdout.write(f'   🟡 Clientes con datos ficticios: {fake_customers.get("total", 0)}')
            self.stdout.write(f'   📈 Total de mapeos: {real_customers.get("total", 0) + fake_customers.get("total", 0)}')
            
        except Exception as e:
            self.stdout.write(f'⚠️ Error obteniendo estadísticas: {str(e)}')



