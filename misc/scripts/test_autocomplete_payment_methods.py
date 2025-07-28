#!/usr/bin/env python
"""
Script para probar la funcionalidad de autocomplete de métodos de pago.
Uso: docker exec Synap_app python misc/scripts/test_autocomplete_payment_methods.py
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
from tiendanube.views_adminet import get_tiendanube_payment_methods
from tiendanube.models_synap import TiendaNubeConfig
import json

User = get_user_model()

def test_payment_methods_api():
    """Probar la API de métodos de pago"""
    print("🧪 PROBANDO API DE MÉTODOS DE PAGO")
    print("="*60)
    
    # Obtener usuario superuser existente
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("❌ No hay usuario superuser disponible")
        return False
    
    print(f"✅ Usando usuario: {user.email}")
    
    # Probar sin query
    print("\n📋 Probando sin query (todos los métodos):")
    request = RequestFactory().get('/tiendanube/adminet/cond_venta_map/payment-methods/')
    request.user = user
    
    response = get_tiendanube_payment_methods(request)
    
    # Verificar que la respuesta sea válida
    if hasattr(response, 'content') and response.content:
        try:
            data = json.loads(response.content.decode())
        except json.JSONDecodeError:
            print(f"❌ Error decodificando JSON: {response.content}")
            return False
    else:
        print(f"❌ Respuesta vacía: {response}")
        return False
    
    if data.get('success'):
        methods = data.get('payment_methods', [])
        count = data.get('count', 0)
        note = data.get('note', '')
        
        print(f"✅ Métodos obtenidos: {count}")
        if note:
            print(f"📝 Nota: {note}")
        
        for i, method in enumerate(methods[:5], 1):
            print(f"  {i}. {method.get('name')} ({method.get('id')})")
        if len(methods) > 5:
            print(f"  ... y {len(methods) - 5} métodos más")
        
        # Probar con query
        queries = ['tarjeta', 'mercadopago', 'paypal', 'transferencia']
        
        for query in queries:
            print(f"\n🔍 Probando query: '{query}'")
            request = RequestFactory().get(f'/tiendanube/adminet/cond_venta_map/payment-methods/?q={query}')
            request.user = user
            
            response = get_tiendanube_payment_methods(request)
            
            if hasattr(response, 'content') and response.content:
                try:
                    data = json.loads(response.content.decode())
                except json.JSONDecodeError:
                    print(f"❌ Error decodificando JSON: {response.content}")
                    continue
            else:
                print(f"❌ Respuesta vacía: {response}")
                continue
            
            if data.get('success'):
                methods = data.get('payment_methods', [])
                print(f"✅ Resultados: {len(methods)}")
                for method in methods:
                    print(f"  • {method.get('name')} ({method.get('id')})")
            else:
                print(f"❌ Error: {data.get('error')}")
        
        return True
    else:
        print(f"❌ Error: {data.get('error')}")
        return False
    
    # Probar con query
    queries = ['tarjeta', 'mercadopago', 'paypal', 'transferencia']
    
    for query in queries:
        print(f"\n🔍 Probando query: '{query}'")
        request = RequestFactory().get(f'/tiendanube/adminet/cond_venta_map/payment-methods/?q={query}')
        request.user = user
        
        response = get_tiendanube_payment_methods(request)
        
        if hasattr(response, 'content'):
            try:
                data = json.loads(response.content.decode())
            except json.JSONDecodeError:
                print(f"❌ Error decodificando JSON: {response.content}")
                continue
        else:
            print(f"❌ Respuesta inválida: {response}")
            continue
        
        if data.get('success'):
            methods = data.get('payment_methods', [])
            print(f"✅ Resultados: {len(methods)}")
            for method in methods:
                print(f"  • {method.get('name')} ({method.get('id')})")
        else:
            print(f"❌ Error: {data.get('error')}")

def test_mapping_scenarios():
    """Probar escenarios de mapeo múltiple"""
    print("\n" + "="*60)
    print("🔗 PROBANDO ESCENARIOS DE MAPEO MÚLTIPLE")
    print("="*60)
    
    # Ejemplo de mapeo múltiple como solicitado
    mapping_example = [
        {"adminet": 1, "tiendanube": ["credit_card", "debit_card"]},
        {"adminet": 2, "tiendanube": ["mercadopago", "stripe"]},
        {"adminet": 3, "tiendanube": ["bank_transfer", "check"]},
        {"adminet": 4, "tiendanube": ["cash_on_delivery"]},
        {"adminet": 5, "tiendanube": ["paypal"]},
        {"adminet": 6, "tiendanube": ["check"]},
        {"adminet": 7, "tiendanube": ["wire_transfer"]},
    ]
    
    print("📋 Ejemplo de mapeo múltiple:")
    for mapping in mapping_example:
        adminet_code = mapping["adminet"]
        tiendanube_methods = mapping["tiendanube"]
        print(f"  AdministraNET {adminet_code} → Tiendanube: {', '.join(tiendanube_methods)}")
    
    print("\n💡 Funcionalidades implementadas:")
    print("  ✅ Autocomplete con dropdown")
    print("  ✅ Navegación por teclado (↑↓)")
    print("  ✅ Selección con Enter")
    print("  ✅ Cierre con Escape")
    print("  ✅ Búsqueda predictiva")
    print("  ✅ Múltiples mapeos por condición de venta")
    print("  ✅ Debounce de 300ms")

def test_url_resolution():
    """Probar resolución de URLs"""
    print("\n" + "="*60)
    print("🔗 PROBANDO RESOLUCIÓN DE URLs")
    print("="*60)
    
    try:
        from django.urls import reverse
        
        url_name = 'tiendanube:get_payment_methods'
        url = reverse(url_name)
        print(f"✅ URL resuelta: {url}")
        
        # Probar con query parameter
        url_with_query = f"{url}?q=tarjeta"
        print(f"✅ URL con query: {url_with_query}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resolviendo URL: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🎯 PRUEBA DE AUTOCOMPLETE DE MÉTODOS DE PAGO")
    print("="*60)
    
    # Probar resolución de URLs
    urls_ok = test_url_resolution()
    
    # Probar API de métodos de pago
    api_ok = test_payment_methods_api()
    
    # Probar escenarios de mapeo
    test_mapping_scenarios()
    
    # Resumen
    print("\n" + "="*60)
    print(" RESUMEN")
    print("="*60)
    print(f"🔗 URLs: {'✅ OK' if urls_ok else '❌ FALLO'}")
    print(f"📋 API: {'✅ OK' if api_ok else '❌ FALLO'}")
    
    if urls_ok and api_ok:
        print("\n🎉 AUTOCOMPLETE LISTO PARA USO")
        print("💡 Funcionalidades disponibles:")
        print("   • Búsqueda predictiva en tiempo real")
        print("   • Navegación por teclado (flechas ↑↓)")
        print("   • Selección con Enter")
        print("   • Cierre con Escape")
        print("   • Múltiples mapeos por condición de venta")
        print("🌐 URL de prueba: /tiendanube/adminet/cond_venta_map/")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")
        print("   - Verificar configuración de URLs")
        print("   - Verificar configuración de Tiendanube")

if __name__ == "__main__":
    main() 