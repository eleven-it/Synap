#!/usr/bin/env python
"""
Script para probar la apariencia visual del dashboard refactorizado
"""

import os
import sys
import django

# Agregar el directorio del proyecto al path
sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from tiendanube_administranet.models import CustomerMapping, SyncLog, TiendanubeConfig, AdministraNETConfig

User = get_user_model()

def test_dashboard_visual():
    print("🎨 === PRUEBA VISUAL DEL DASHBOARD REFACTORIZADO ===")
    
    # Crear datos de prueba para visualización
    print("\n📊 Creando datos de prueba...")
    
    # Crear configuraciones de prueba
    tiendanube_config, created = TiendanubeConfig.objects.get_or_create(
        store_id="test_store_123",
        defaults={
            'name': 'Test Tiendanube Config',
            'access_token': 'test_token_123',
            'api_url': 'https://api.tiendanube.com/v1'
        }
    )
    
    adminet_config, created = AdministraNETConfig.objects.get_or_create(
        host="localhost",
        defaults={
            'name': 'Test Adminet Config',
            'port': 3306,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_password'
        }
    )
    
    # Crear mapeos de prueba
    mappings_data = [
        {
            'tiendanube_email': 'cliente1@example.com',
            'adminet_codigo': 1001,
            'sync_status': 'synced',
            'sync_enabled': True
        },
        {
            'tiendanube_email': 'cliente2@example.com',
            'adminet_codigo': 1002,
            'sync_status': 'pending',
            'sync_enabled': True
        },
        {
            'tiendanube_email': 'cliente3@example.com',
            'adminet_codigo': 1003,
            'sync_status': 'error',
            'sync_enabled': False
        },
        {
            'tiendanube_email': 'cliente4@example.com',
            'adminet_codigo': 1004,
            'sync_status': 'synced',
            'sync_enabled': True
        },
        {
            'tiendanube_email': 'cliente5@example.com',
            'adminet_codigo': 1005,
            'sync_status': 'pending',
            'sync_enabled': True
        }
    ]
    
    for mapping_data in mappings_data:
        CustomerMapping.objects.get_or_create(
            tiendanube_email=mapping_data['tiendanube_email'],
            defaults=mapping_data
        )
    
    # Crear logs de sincronización de prueba
    logs_data = [
        {
            'sync_type': 'customer_sync',
            'status': 'success',
            'platform': 'tiendanube',
            'message': 'Synchronized 5 customers from Tiendanube'
        },
        {
            'sync_type': 'customer_sync',
            'status': 'success',
            'platform': 'adminet',
            'message': 'Synchronized 3 customers from AdministraNET'
        },
        {
            'sync_type': 'mapping_update',
            'status': 'warning',
            'platform': 'tiendanube',
            'message': 'Updated mapping for cliente2@example.com'
        },
        {
            'sync_type': 'customer_sync',
            'status': 'error',
            'platform': 'tiendanube',
            'message': 'Failed to sync cliente3@example.com'
        }
    ]
    
    for log_data in logs_data:
        SyncLog.objects.get_or_create(
            sync_type=log_data['sync_type'],
            status=log_data['status'],
            platform=log_data['platform'],
            defaults={'message': log_data['message']}
        )
    
    print("✅ Datos de prueba creados exitosamente")
    
    # Probar el dashboard
    print("\n🌐 Probando el dashboard...")
    
    client = Client()
    
    # Obtener usuario admin
    try:
        user = User.objects.get(email='admin@example.com')
        print(f"✅ Usuario encontrado: {user.email}")
    except User.DoesNotExist:
        print("❌ Usuario admin no encontrado")
        return
    
    # Simular sesión
    session_data = {
        'user': {
            'uid': getattr(user, 'uid', user.id),
            'email': user.email,
            'idioma': 'es'
        }
    }
    session = client.session
    session.update(session_data)
    session.save()
    
    # Probar dashboard
    response = client.get('/tiendanube-adminet/', follow=True)
    
    if response.status_code == 200:
        print("✅ Dashboard accesible")
        
        # Analizar contenido del dashboard
        content = response.content.decode('utf-8')
        
        # Verificar elementos del nuevo diseño
        design_elements = {
            'Welcome Section': 'Welcome to Integration Dashboard' in content,
            'Gradient Header': 'bg-gradient-to-r from-blue-600 to-purple-600' in content,
            'Statistics Cards': 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4' in content,
            'System Status': 'System Status' in content,
            'Recent Mappings': 'Recent Mappings' in content,
            'Quick Actions': 'Quick Actions' in content,
            'Recent Activity': 'Recent Activity' in content,
            'System Information': 'System Information' in content,
            'Modern Buttons': 'btn btn-primary' in content,
            'Badges': 'badge badge-' in content,
            'Icons': 'icon-sm' in content,
            'Responsive Grid': 'xl:grid-cols-3' in content,
            'Hover Effects': 'hover:shadow-lg' in content,
            'Dark Mode Support': 'dark:bg-gray-900' in content,
            'Animations': 'transition-all duration-300' in content
        }
        
        print("\n🎨 ELEMENTOS DE DISEÑO DETECTADOS:")
        for element, found in design_elements.items():
            status = "✅" if found else "❌"
            print(f"  {status} {element}")
        
        # Verificar funcionalidades JavaScript
        js_features = {
            'IntegrationApp': 'const IntegrationApp' in content,
            'Toast Notifications': 'showToast' in content,
            'Confirmation Dialogs': 'confirmAction' in content,
            'Loading States': 'loading-spinner' in content,
            'Auto-refresh': 'setInterval' in content,
            'AJAX Functions': 'sendData' in content,
            'Debounce': 'debounce' in content
        }
        
        print("\n⚡ FUNCIONALIDADES JAVASCRIPT:")
        for feature, found in js_features.items():
            status = "✅" if found else "❌"
            print(f"  {status} {feature}")
        
        # Verificar datos mostrados
        data_elements = {
            'Total Mappings': 'Total Mappings' in content,
            'Synced Count': 'synced_mappings' in content,
            'Pending Count': 'pending_mappings' in content,
            'Error Count': 'error_mappings' in content,
            'Connection Status': 'Connected' in content,
            'Recent Mappings List': 'cliente1@example.com' in content,
            'Activity Logs': 'customer_sync' in content,
            'Success Rate': 'Success Rate' in content
        }
        
        print("\n📊 DATOS MOSTRADOS:")
        for element, found in data_elements.items():
            status = "✅" if found else "❌"
            print(f"  {status} {element}")
        
        # Estadísticas del contenido
        print("\n📈 ESTADÍSTICAS DEL DASHBOARD:")
        print(f"  • Tamaño del contenido: {len(content):,} caracteres")
        print(f"  • Líneas de código: {content.count(chr(10)):,}")
        print(f"  • Elementos CSS: {content.count('class='):,}")
        print(f"  • Elementos JavaScript: {content.count('function'):,}")
        print(f"  • Iconos SVG: {content.count('<svg'):,}")
        print(f"  • Gradientes: {content.count('gradient-to-'):,}")
        
        # Verificar responsividad
        responsive_features = {
            'Mobile First': 'sm:grid-cols-2' in content,
            'Tablet Breakpoints': 'md:grid-cols-2' in content,
            'Desktop Breakpoints': 'lg:grid-cols-4' in content,
            'Large Desktop': 'xl:grid-cols-3' in content,
            'Responsive Text': 'text-sm sm:text-base' in content,
            'Responsive Spacing': 'px-4 sm:px-6' in content
        }
        
        print("\n📱 CARACTERÍSTICAS RESPONSIVAS:")
        for feature, found in responsive_features.items():
            status = "✅" if found else "❌"
            print(f"  {status} {feature}")
        
        # Verificar accesibilidad
        accessibility_features = {
            'Semantic HTML': '<h1>' in content and '<h2>' in content and '<h3>' in content,
            'ARIA Labels': 'aria-label' in content,
            'Focus States': 'focus:ring' in content,
            'Keyboard Navigation': 'tabindex' in content,
            'Screen Reader Support': 'sr-only' in content or 'aria-hidden' in content
        }
        
        print("\n♿ CARACTERÍSTICAS DE ACCESIBILIDAD:")
        for feature, found in accessibility_features.items():
            status = "✅" if found else "❌"
            print(f"  {status} {feature}")
        
        print("\n🎯 RESUMEN DEL DISEÑO:")
        total_elements = len(design_elements) + len(js_features) + len(data_elements) + len(responsive_features) + len(accessibility_features)
        found_elements = sum(design_elements.values()) + sum(js_features.values()) + sum(data_elements.values()) + sum(responsive_features.values()) + sum(accessibility_features.values())
        coverage = (found_elements / total_elements) * 100
        
        print(f"  • Cobertura total: {coverage:.1f}%")
        print(f"  • Elementos implementados: {found_elements}/{total_elements}")
        
        if coverage >= 90:
            print("  🏆 EXCELENTE: El dashboard tiene un diseño moderno y completo")
        elif coverage >= 75:
            print("  👍 BUENO: El dashboard tiene un diseño sólido")
        elif coverage >= 60:
            print("  ⚠️ REGULAR: El dashboard necesita mejoras")
        else:
            print("  ❌ DEFICIENTE: El dashboard necesita una refactorización completa")
            
    else:
        print(f"❌ Error accediendo al dashboard: {response.status_code}")
        print(f"  Contenido: {response.content[:500]}...")

if __name__ == "__main__":
    test_dashboard_visual() 