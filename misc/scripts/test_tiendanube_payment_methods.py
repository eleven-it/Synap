#!/usr/bin/env python
"""
Script para probar la obtención de métodos de pago de Tiendanube.
Uso: docker exec Synap_app python misc/scripts/test_tiendanube_payment_methods.py
"""

import os
import sys
import django
import requests

# Agregar el directorio raíz al path
sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube.models_synap import TiendaNubeConfig
from tiendanube.services_main import TiendaNubeService

def test_payment_methods():
    """Probar obtención de métodos de pago de Tiendanube"""
    print("🔍 PROBANDO OBTENCIÓN DE MÉTODOS DE PAGO DE TIENDANUBE")
    print("="*60)
    
    # Obtener configuración
    config = TiendaNubeConfig.objects.first()
    if not config:
        print("❌ No hay configuración de Tiendanube")
        return False
    
    print(f"✅ Configuración encontrada:")
    print(f"   Store ID: {config.store_id}")
    print(f"   API URL: {config.api_url}")
    print(f"   Token configurado: {'Sí' if config.access_token else 'No'}")
    
    # Crear servicio
    service = TiendaNubeService(config)
    
    # Probar conexión
    print("\n🔗 Probando conexión...")
    connection_success, connection_message = service.test_connection()
    print(f"   Conexión: {'✅ OK' if connection_success else '❌ FALLO'}")
    print(f"   Mensaje: {connection_message}")
    
    if not connection_success:
        print("❌ No se puede obtener métodos de pago sin conexión")
        return False
    
    # Obtener métodos de pago
    print("\n💳 Obteniendo métodos de pago...")
    result = service.get_payment_methods()
    
    if result.get('success'):
        payment_methods = result.get('payment_methods', [])
        count = result.get('count', 0)
        
        print(f"✅ Métodos de pago obtenidos exitosamente")
        print(f"📊 Total de métodos: {count}")
        
        if payment_methods:
            print("\n📋 Métodos de pago disponibles:")
            for i, method in enumerate(payment_methods[:10], 1):  # Mostrar solo los primeros 10
                print(f"  {i}. {method.get('name', 'Sin nombre')} (ID: {method.get('id', 'N/A')})")
                if method.get('description'):
                    print(f"     Descripción: {method['description']}")
                if method.get('type'):
                    print(f"     Tipo: {method['type']}")
                print()
            
            if count > 10:
                print(f"   ... y {count - 10} métodos más")
            
            # Mostrar estructura del primer método como ejemplo
            if payment_methods:
                print("📝 Estructura de datos del primer método:")
                first_method = payment_methods[0]
                for key, value in first_method.items():
                    print(f"   {key}: {value}")
        
        return True
    else:
        error = result.get('error', 'Error desconocido')
        print(f"❌ Error obteniendo métodos de pago: {error}")
        return False

def test_payment_methods_from_orders():
    """Probar obtención de métodos de pago desde órdenes existentes"""
    print("\n" + "="*60)
    print("🔍 PROBANDO MÉTODOS DE PAGO DESDE ÓRDENES EXISTENTES")
    print("="*60)
    
    # Obtener configuración
    config = TiendaNubeConfig.objects.first()
    if not config:
        print("❌ No hay configuración de Tiendanube")
        return False
    
    service = TiendaNubeService(config)
    
    # Obtener algunas órdenes para extraer métodos de pago
    print("📦 Obteniendo órdenes recientes...")
    try:
        response = requests.get(f"{service.BASE_URL}/orders", headers=service.headers, params={'limit': 10})
        
        if response.status_code == 200:
            orders = response.json()
            print(f"✅ Órdenes obtenidas: {len(orders)} órdenes")
            
            # Extraer métodos de pago únicos
            payment_methods = set()
            for order in orders:
                if 'payment_method' in order and order['payment_method']:
                    payment_methods.add(order['payment_method'])
            
            print(f"💳 Métodos de pago encontrados en órdenes: {len(payment_methods)}")
            if payment_methods:
                print("📋 Métodos de pago:")
                for i, method in enumerate(payment_methods, 1):
                    print(f"  {i}. {method}")
            
            return True
        else:
            print(f"❌ Error obteniendo órdenes: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🎯 PRUEBA DE MÉTODOS DE PAGO DE TIENDANUBE")
    print("="*60)
    
    # Probar obtención directa de métodos de pago
    payment_methods_ok = test_payment_methods()
    
    # Probar obtención desde órdenes
    orders_ok = test_payment_methods_from_orders()
    
    # Resumen
    print("\n" + "="*60)
    print(" RESUMEN")
    print("="*60)
    print(f"💳 Métodos de pago directos: {'✅ OK' if payment_methods_ok else '❌ FALLO'}")
    print(f"📦 Métodos desde órdenes: {'✅ OK' if orders_ok else '❌ FALLO'}")
    
    if payment_methods_ok or orders_ok:
        print("\n🎉 PRUEBAS COMPLETADAS")
        print("💡 Los métodos de pago están disponibles para mapeo")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")
        print("   - Verificar configuración de Tiendanube")
        print("   - Verificar conectividad con la API")

if __name__ == "__main__":
    main() 