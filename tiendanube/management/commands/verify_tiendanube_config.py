from django.core.management.base import BaseCommand
from django.conf import settings
from tiendanube.models import TiendaNubeConfig
from tiendanube.services import TiendaNubeService
import requests
import json

class Command(BaseCommand):
    help = 'Verifica y actualiza la configuración de TiendaNube'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-token',
            action='store_true',
            help='Actualizar el token de acceso',
        )
        parser.add_argument(
            '--new-token',
            type=str,
            help='Nuevo token de acceso',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== VERIFICACIÓN DE CONFIGURACIÓN TIENDANUBE ==='))
        
        # Obtener configuración actual
        config = TiendaNubeConfig.objects.first()
        if not config:
            self.stdout.write(self.style.ERROR('No se encontró configuración de TiendaNube'))
            return
        
        self.stdout.write(f'Store ID: {config.store_id}')
        self.stdout.write(f'API URL: {config.api_url}')
        self.stdout.write(f'Token actual: {config.access_token[:10]}...{config.access_token[-10:] if config.access_token else "None"}')
        
        # Verificar variables de entorno
        env_token = getattr(settings, 'TIENDANUBE_ACCESS_TOKEN', '')
        env_store_id = getattr(settings, 'TIENDANUBE_STORE_ID', '')
        
        self.stdout.write(f'\n=== VARIABLES DE ENTORNO ===')
        self.stdout.write(f'TIENDANUBE_ACCESS_TOKEN: {env_token[:10]}...{env_token[-10:] if env_token else "None"}')
        self.stdout.write(f'TIENDANUBE_STORE_ID: {env_store_id}')
        
        # Actualizar token si se solicita
        if options['update_token'] and options['new_token']:
            config.access_token = options['new_token']
            config.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Token actualizado: {config.access_token[:10]}...{config.access_token[-10:]}'))
        
        # Probar diferentes formatos de headers
        self.stdout.write(f'\n=== PROBANDO DIFERENTES FORMATOS DE HEADERS ===')
        
        headers_variants = [
            {
                "Content-Type": "application/json",
                "Authentication": f"bearer {config.access_token}",
                "User-Agent": "Synap (https://synap.com.ar)"
            },
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.access_token}",
                "User-Agent": "Synap (https://synap.com.ar)"
            },
            {
                "Content-Type": "application/json",
                "Authentication": f"Bearer {config.access_token}",
                "User-Agent": "Synap (https://synap.com.ar)"
            }
        ]
        
        for i, headers in enumerate(headers_variants, 1):
            self.stdout.write(f'\n--- Variante {i} ---')
            self.stdout.write(f'Headers: {json.dumps(headers, indent=2)}')
            
            try:
                url = f"{config.api_url}/products?limit=1"
                response = requests.get(url, headers=headers, timeout=10)
                
                self.stdout.write(f'Status Code: {response.status_code}')
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f'✅ ÉXITO con variante {i}'))
                    self.stdout.write(f'Response: {response.text[:200]}...')
                    break
                else:
                    self.stdout.write(self.style.WARNING(f'❌ Error {response.status_code}: {response.text}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Exception: {str(e)}'))
        
        # Verificar documentación de la API
        self.stdout.write(f'\n=== INFORMACIÓN ADICIONAL ===')
        self.stdout.write('Para obtener un nuevo token válido:')
        self.stdout.write('1. Ve a https://www.tiendanube.com/apps/')
        self.stdout.write('2. Crea una nueva aplicación')
        self.stdout.write('3. Configura los permisos necesarios (products, orders, etc.)')
        self.stdout.write('4. Obtén el token de acceso')
        self.stdout.write('5. Ejecuta: python manage.py verify_tiendanube_config --update-token --new-token TU_NUEVO_TOKEN') 