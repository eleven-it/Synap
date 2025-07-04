from django.core.management.base import BaseCommand
from django.test import RequestFactory
from core.middleware import DeviceDetectionMiddleware
import re

class Command(BaseCommand):
    help = 'Prueba la detección de dispositivos móviles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-agent',
            type=str,
            help='User agent específico para probar'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 Probando detección de dispositivos...'))
        
        # User agents de prueba
        test_user_agents = [
            # Móviles
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            
            # Desktop
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]
        
        # Si se proporciona un user agent específico, usarlo
        if options['user_agent']:
            test_user_agents = [options['user_agent']]
        
        # Crear factory para requests
        factory = RequestFactory()
        middleware = DeviceDetectionMiddleware(lambda request: None)
        
        self.stdout.write("=" * 80)
        
        for i, user_agent in enumerate(test_user_agents, 1):
            # Crear request con el user agent
            request = factory.get('/')
            request.META['HTTP_USER_AGENT'] = user_agent
            
            # Procesar con el middleware
            middleware.process_request(request)
            
            # Mostrar resultados
            status = "📱 MÓVIL" if request.is_mobile else "💻 DESKTOP"
            device_type = getattr(request, 'device_type', 'unknown')
            
            self.stdout.write(f"{i:2d}. {status} | {device_type:12s} | {user_agent[:80]}...")
            
            # Mostrar detalles adicionales
            self.stdout.write(f"     is_mobile: {request.is_mobile}")
            self.stdout.write(f"     is_desktop: {request.is_desktop}")
            self.stdout.write(f"     device_type: {device_type}")
            self.stdout.write("-" * 40)
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS('✅ Prueba completada'))
        
        # Mostrar información sobre templates
        self.stdout.write("\n🎨 Templates disponibles:")
        self.stdout.write("Desktop:")
        self.stdout.write("  - login/login.html")
        self.stdout.write("  - login/register.html")
        self.stdout.write("  - login/index.html")
        self.stdout.write("Mobile:")
        self.stdout.write("  - login/login_mobile.html")
        self.stdout.write("  - login/register_mobile.html")
        self.stdout.write("  - login/index_mobile.html") 