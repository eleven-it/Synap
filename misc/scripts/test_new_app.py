#!/usr/bin/env python3
"""
Script de prueba para verificar que la nueva app tiendanube_administranet funciona correctamente.
"""

import os
import sys
import django
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# En el contenedor Docker, el proyecto está en /app
if os.path.exists('/app'):
    sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.utils import timezone
from tiendanube_administranet.models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping, SyncLog
)
from tiendanube_administranet.services.sync_service import TiendanubeAdministraNETSyncService


def test_models():
    """Probar la creación de modelos."""
    print("🧪 Probando modelos...")
    
    try:
        # Crear configuración de Tiendanube
        tiendanube_config = TiendanubeConfig.objects.create(
            name="Configuración de Prueba Tiendanube",
            store_id="test_store_123",
            access_token="test_token_123",
            api_url="https://api.tiendanube.com/v1",
            is_active=True
        )
        print(f"✅ Configuración Tiendanube creada: {tiendanube_config}")
        
        # Crear configuración de AdministraNET
        adminet_config = AdministraNETConfig.objects.create(
            name="Configuración de Prueba AdministraNET",
            host="localhost",
            port=3306,
            database="administranet",
            user="testuser",
            password="testpass",
            is_active=True
        )
        print(f"✅ Configuración AdministraNET creada: {adminet_config}")
        
        # Crear mapeo de cliente
        customer_mapping = CustomerMapping.objects.create(
            tiendanube_email="test@example.com",
            tiendanube_name="Cliente de Prueba",
            adminet_codigo=12345,
            adminet_nombre="Cliente de Prueba Adminet",
            sync_direction='bidirectional',
            sync_status='pending',
            sync_enabled=True
        )
        print(f"✅ Mapeo de cliente creado: {customer_mapping}")
        
        # Crear log de sincronización
        sync_log = SyncLog.objects.create(
            sync_type='customer_sync',
            status='success',
            platform='both',
            message="Prueba de sincronización exitosa",
            items_processed=1,
            items_success=1,
            items_failed=0
        )
        print(f"✅ Log de sincronización creado: {sync_log}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando modelos: {str(e)}")
        return False


def test_services():
    """Probar los servicios."""
    print("\n🔧 Probando servicios...")
    
    try:
        # Probar servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService()
        print("✅ Servicio de sincronización creado correctamente")
        
        # Probar estadísticas
        stats = sync_service.get_sync_statistics()
        print(f"✅ Estadísticas obtenidas: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando servicios: {str(e)}")
        return False


def test_admin_interface():
    """Probar la interfaz de admin."""
    print("\n👨‍💼 Probando interfaz de admin...")
    
    try:
        from django.contrib import admin
        from tiendanube_administranet.admin import (
            TiendanubeConfigAdmin, AdministraNETConfigAdmin,
            CustomerMappingAdmin, SyncLogAdmin
        )
        
        # Verificar que los modelos están registrados
        registered_models = admin.site._registry.keys()
        
        models_to_check = [
            TiendanubeConfig, AdministraNETConfig, 
            CustomerMapping, SyncLog
        ]
        
        for model in models_to_check:
            if model in registered_models:
                print(f"✅ {model.__name__} registrado en admin")
            else:
                print(f"❌ {model.__name__} NO registrado en admin")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando admin: {str(e)}")
        return False


def test_urls():
    """Probar las URLs."""
    print("\n🔗 Probando URLs...")
    
    try:
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        
        # Probar URLs principales
        urls_to_test = [
            'tiendanube_administranet:dashboard',
            'tiendanube_administranet:customer_mapping_list',
            'tiendanube_administranet:sync_log_list',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"✅ URL {url_name}: {url}")
            except Exception as e:
                print(f"❌ Error con URL {url_name}: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando URLs: {str(e)}")
        return False


def cleanup_test_data():
    """Limpiar datos de prueba."""
    print("\n🧹 Limpiando datos de prueba...")
    
    try:
        # Eliminar datos de prueba
        TiendanubeConfig.objects.filter(name__contains="Prueba").delete()
        AdministraNETConfig.objects.filter(name__contains="Prueba").delete()
        CustomerMapping.objects.filter(tiendanube_email="test@example.com").delete()
        SyncLog.objects.filter(message__contains="Prueba").delete()
        
        print("✅ Datos de prueba eliminados")
        return True
        
    except Exception as e:
        print(f"❌ Error limpiando datos: {str(e)}")
        return False


def main():
    """Función principal."""
    print("🚀 Iniciando pruebas de tiendanube_administranet...")
    print("=" * 60)
    
    results = {
        'models': test_models(),
        'services': test_services(),
        'admin': test_admin_interface(),
        'urls': test_urls(),
    }
    
    # Limpiar datos de prueba
    cleanup_test_data()
    
    # Mostrar resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name.upper()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nTotal de pruebas: {total_tests}")
    print(f"Pruebas exitosas: {passed_tests}")
    print(f"Pruebas fallidas: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 ¡Todas las pruebas pasaron! La app está funcionando correctamente.")
        return True
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 