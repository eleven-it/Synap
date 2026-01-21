from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
import logging

from inventario.models import TiendaNubeConfig
from inventario.services.tiendanube import TiendaNubeService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza productos y stock con TiendaNube'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['products', 'stock', 'full'],
            default='full',
            help='Tipo de sincronización a realizar'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Límite de productos a sincronizar'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar sincronización incluso si no está configurada la automática'
        )
        parser.add_argument(
            '--config-id',
            type=int,
            help='ID específico de configuración a usar'
        )
        parser.add_argument(
            '--create-config',
            action='store_true',
            help='Crear configuración automáticamente desde variables de entorno'
        )

    def handle(self, *args, **options):
        sync_type = options['type']
        limit = options['limit']
        force = options['force']
        config_id = options['config_id']
        create_config = options['create_config']

        self.stdout.write(
            self.style.SUCCESS(f'Iniciando sincronización {sync_type} con TiendaNube...')
        )

        try:
            # Obtener configuración
            config = None
            
            if config_id:
                config = TiendaNubeConfig.objects.get(id=config_id)
            else:
                config = TiendaNubeConfig.objects.first()
                
                # Si no existe configuración y se solicita crear automáticamente
                if not config and create_config:
                    config = self._create_config_from_env()
                elif not config:
                    # Intentar crear configuración automáticamente desde variables de entorno
                    config = self._create_config_from_env()

            if not config:
                self.stdout.write(
                    self.style.ERROR('No se encontró configuración de TiendaNube')
                )
                self.stdout.write(
                    self.style.WARNING('Usa --create-config para crear configuración desde variables de entorno')
                )
                return

            if not config.is_configured:
                self.stdout.write(
                    self.style.ERROR('Configuración de TiendaNube incompleta')
                )
                self.stdout.write(
                    self.style.WARNING('Verifica las variables de entorno: TIENDANUBE_STORE_ID y TIENDANUBE_ACCESS_TOKEN')
                )
                return

            # Verificar si debe ejecutarse automáticamente
            if not force and not config.auto_sync:
                self.stdout.write(
                    self.style.WARNING('Sincronización automática desactivada. Usa --force para ejecutar.')
                )
                return

            # Verificar intervalo de sincronización
            if not force and config.last_sync:
                time_since_last = timezone.now() - config.last_sync
                if time_since_last.total_seconds() < (config.sync_interval * 60):
                    self.stdout.write(
                        self.style.WARNING(
                            f'Sincronización reciente. Próxima en {(config.sync_interval * 60 - time_since_last.total_seconds()) / 60:.1f} minutos'
                        )
                    )
                    return

            # Inicializar servicio
            service = TiendaNubeService(config)

            # Ejecutar sincronización según tipo
            if sync_type == 'products' or sync_type == 'full':
                self.stdout.write('Sincronizando productos...')
                success, failed = service.sync_products_from_tiendanube(limit=limit)
                self.stdout.write(
                    self.style.SUCCESS(f'Productos: {success} exitosos, {failed} fallidos')
                )

            if sync_type == 'stock' or sync_type == 'full':
                self.stdout.write('Sincronizando stock...')
                success, failed = service.sync_stock_to_tiendanube()
                self.stdout.write(
                    self.style.SUCCESS(f'Stock: {success} exitosos, {failed} fallidos')
                )

            # Actualizar última sincronización
            config.last_sync = timezone.now()
            config.save()

            self.stdout.write(
                self.style.SUCCESS('Sincronización completada exitosamente')
            )

        except Exception as e:
            logger.error(f'Error en sincronización: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error en sincronización: {e}')
            )
            raise

    def _create_config_from_env(self):
        """Crea configuración desde variables de entorno"""
        try:
            store_id = getattr(settings, 'TIENDANUBE_STORE_ID', '')
            access_token = getattr(settings, 'TIENDANUBE_ACCESS_TOKEN', '')
            webhook_secret = getattr(settings, 'TIENDANUBE_WEBHOOK_SECRET', '')
            api_url = getattr(settings, 'TIENDANUBE_API_URL', 'https://api.tiendanube.com/v1')
            auto_sync = getattr(settings, 'TIENDANUBE_AUTO_SYNC', True)
            sync_interval = getattr(settings, 'TIENDANUBE_SYNC_INTERVAL', 30)
            
            if not store_id or not access_token:
                self.stdout.write(
                    self.style.ERROR('Variables de entorno TIENDANUBE_STORE_ID y TIENDANUBE_ACCESS_TOKEN son requeridas')
                )
                return None
            
            config = TiendaNubeConfig.objects.create(
                store_id=store_id,
                access_token=access_token,
                webhook_secret=webhook_secret,
                api_url=api_url,
                auto_sync=auto_sync,
                sync_interval=sync_interval
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Configuración creada automáticamente para store: {store_id}')
            )
            
            return config
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creando configuración: {e}')
            )
            return None 