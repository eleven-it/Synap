from django.core.management.base import BaseCommand
from django.conf import settings
from tiendanube.models import TiendaNubeConfig
from tiendanube.services import TiendaNubeService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Prueba la conexión con TiendaNube y muestra logs detallados'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== PRUEBA DE CONEXIÓN TIENDANUBE ==='))
        
        # Obtener configuración
        config = TiendaNubeConfig.objects.first()
        if not config:
            self.stdout.write(self.style.ERROR('No se encontró configuración de TiendaNube'))
            return
        
        self.stdout.write(f'Store ID: {config.store_id}')
        self.stdout.write(f'API URL: {config.api_url}')
        self.stdout.write(f'Access Token: {config.access_token[:10]}...{config.access_token[-10:] if config.access_token else "None"}')
        self.stdout.write(f'Auto Sync: {config.auto_sync}')
        
        # Crear servicio y probar conexión
        service = TiendaNubeService(config)
        
        self.stdout.write('\n=== PROBANDO CONEXIÓN ===')
        success, message = service.test_connection()
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'✅ Conexión exitosa: {message}'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Error de conexión: {message}'))
        
        # Probar creación de producto
        self.stdout.write('\n=== PROBANDO CREACIÓN DE PRODUCTO ===')
        test_product_data = {
            "name": "Producto de Prueba",
            "description": "Descripción de prueba",
            "price": 100.0,
            "sku": "TEST001",
            "handle": "producto-prueba",
            "published": False,
        }
        
        self.stdout.write(f'Datos del producto de prueba: {test_product_data}')
        
        response = service.create_product(test_product_data)
        self.stdout.write(f'Respuesta: {response}')
        
        if response and response.get("id"):
            self.stdout.write(self.style.SUCCESS(f'✅ Producto creado exitosamente con ID: {response["id"]}'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Error creando producto: {response}')) 