from django.core.management.base import BaseCommand
from django.conf import settings
from core.utils.cdn import get_cdn_status, validate_cdn_configuration, test_cdn_performance
import json

class Command(BaseCommand):
    help = 'Prueba y valida la configuración del CDN'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada',
        )
        parser.add_argument(
            '--test-performance',
            action='store_true',
            help='Probar rendimiento del CDN',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Test de Configuración CDN ===\n'))
        
        # Obtener estado del CDN
        status = get_cdn_status()
        
        self.stdout.write(f"Estado del CDN: {'✅ Habilitado' if status['enabled'] else '❌ Deshabilitado'}")
        if status['enabled']:
            self.stdout.write(f"Proveedor: {status['provider']}")
            self.stdout.write(f"Dominio: {status['domain']}")
            self.stdout.write(f"MEDIA_URL: {status['media_url']}")
            self.stdout.write(f"STATIC_URL: {status['static_url']}")
        
        # Validar configuración
        errors, warnings = validate_cdn_configuration()
        
        if errors:
            self.stdout.write('\n❌ Errores de configuración:')
            for error in errors:
                self.stdout.write(f"  - {error}")
        
        if warnings:
            self.stdout.write('\n⚠️  Advertencias:')
            for warning in warnings:
                self.stdout.write(f"  - {warning}")
        
        if not errors and not warnings and status['enabled']:
            self.stdout.write('\n✅ Configuración válida')
        
        # Probar rendimiento si se solicita
        if options['test_performance'] and status['enabled']:
            self.stdout.write('\n=== Test de Rendimiento ===')
            performance = test_cdn_performance()
            
            if performance:
                self.stdout.write(f"URL de prueba: {performance['url']}")
                self.stdout.write(f"Status Code: {performance['status_code']}")
                self.stdout.write(f"Tiempo de respuesta: {performance['response_time']}ms")
                self.stdout.write(f"Tamaño del contenido: {performance['content_length']} bytes")
                
                if options['verbose']:
                    self.stdout.write('\nHeaders de respuesta:')
                    for header, value in performance['headers'].items():
                        self.stdout.write(f"  {header}: {value}")
            else:
                self.stdout.write(self.style.ERROR('❌ No se pudo probar el rendimiento'))
        
        # Mostrar información adicional si es verbose
        if options['verbose']:
            self.stdout.write('\n=== Información Detallada ===')
            self.stdout.write(f"Configuración actual:")
            self.stdout.write(f"  USE_CLOUDFLARE_CDN: {getattr(settings, 'USE_CLOUDFLARE_CDN', False)}")
            self.stdout.write(f"  USE_AWS_CDN: {getattr(settings, 'USE_AWS_CDN', False)}")
            self.stdout.write(f"  USE_BUNNY_CDN: {getattr(settings, 'USE_BUNNY_CDN', False)}")
            
            if hasattr(settings, 'CDN_CACHE_HEADERS'):
                self.stdout.write(f"  CDN_CACHE_HEADERS: {json.dumps(settings.CDN_CACHE_HEADERS, indent=2)}")
        
        self.stdout.write('\n=== Fin del Test ===') 