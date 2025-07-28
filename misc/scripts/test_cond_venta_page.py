#!/usr/bin/env python
"""
Script para probar la página de mapeo de condiciones de venta.
Uso: docker exec Synap_app python misc/scripts/test_cond_venta_page.py
"""

import os
import sys
import django

# Agregar el directorio raíz al path
sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from tiendanube.views_adminet import CondVentaMapListView
from tiendanube.models_adminet import TiendaNubeAdminetConfig

User = get_user_model()

def test_view():
    """Probar la vista de mapeo de condiciones de venta"""
    print("🧪 PROBANDO VISTA DE MAPEO DE CONDICIONES DE VENTA")
    
    # Crear un request factory
    factory = RequestFactory()
    
    # Crear un usuario de prueba (superuser)
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'nombre': 'Test Admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Usuario de prueba creado: {user.email}")
    else:
        print(f"✅ Usuario de prueba existente: {user.email}")
    
    # Crear request
    request = factory.get('/tiendanube/adminet/cond_venta_map/')
    request.user = user
    
    # Probar la vista
    try:
        view = CondVentaMapListView()
        view.request = request
        view.setup(request)
        
        # Obtener contexto
        context = view.get_context_data()
        
        print("✅ Vista ejecutada correctamente")
        print(f"📊 Condiciones de venta encontradas: {len(context.get('condiciones_venta', []))}")
        print(f"🔗 Conexión exitosa: {context.get('connection_success', False)}")
        
        if context.get('connection_error'):
            print(f"❌ Error de conexión: {context['connection_error']}")
        
        if context.get('condiciones_venta'):
            print("\n📋 Primeras 3 condiciones de venta:")
            for i, cond in enumerate(context['condiciones_venta'][:3]):
                print(f"  {i+1}. Código: {cond['codigo']}, Descripción: {cond['descripcion']}")
                print(f"     Mapeado: {cond['mapeado']}, Activo: {cond['activo']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en la vista: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_url_resolution():
    """Probar resolución de URLs"""
    print("\n🔍 PROBANDO RESOLUCIÓN DE URLs")
    
    try:
        from django.urls import reverse
        
        urls_to_test = [
            'tiendanube:cond_venta_map_list',
            'tiendanube:cond_venta_map_toggle',
            'tiendanube:cond_venta_map_delete_ajax',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"✅ {url_name}: {url}")
            except Exception as e:
                print(f"❌ {url_name}: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando URLs: {str(e)}")
        return False

def test_adminet_config():
    """Probar configuración de administraNET"""
    print("\n🔍 PROBANDO CONFIGURACIÓN ADMINISTRANET")
    
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    
    if config:
        print(f"✅ Configuración activa encontrada:")
        print(f"   Host: {config.host}")
        print(f"   Puerto: {config.port}")
        print(f"   Base de datos: {config.database}")
        print(f"   Usuario: {config.user}")
        print(f"   Última actualización: {config.updated_at}")
        return True
    else:
        print("❌ No hay configuración activa de administraNET")
        return False

def main():
    """Función principal"""
    print("="*60)
    print(" PRUEBA DE PÁGINA DE MAPEO DE CONDICIONES DE VENTA")
    print("="*60)
    
    # Probar configuración
    config_ok = test_adminet_config()
    
    # Probar URLs
    urls_ok = test_url_resolution()
    
    # Probar vista
    if config_ok and urls_ok:
        view_ok = test_view()
    else:
        view_ok = False
    
    # Resumen
    print("\n" + "="*60)
    print(" RESUMEN")
    print("="*60)
    print(f"🔧 Configuración administraNET: {'✅ OK' if config_ok else '❌ FALLO'}")
    print(f"🔗 URLs: {'✅ OK' if urls_ok else '❌ FALLO'}")
    print(f"👁️  Vista: {'✅ OK' if view_ok else '❌ FALLO'}")
    
    if config_ok and urls_ok and view_ok:
        print("\n🎉 TODAS LAS PRUEBAS PASARON")
        print("💡 La página está lista para usar")
        print("🌐 URL: http://localhost:8002/tiendanube/adminet/cond_venta_map/")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")
        if not config_ok:
            print("   - Configurar conexión administraNET")
        if not urls_ok:
            print("   - Verificar configuración de URLs")
        if not view_ok:
            print("   - Verificar permisos y configuración de vista")

if __name__ == "__main__":
    main() 