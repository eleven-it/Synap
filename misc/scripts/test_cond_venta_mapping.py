#!/usr/bin/env python
"""
Script de prueba para verificar la funcionalidad de mapeo de condiciones de venta.
Uso: docker exec Synap_app python misc/scripts/test_cond_venta_mapping.py
"""

import os
import sys
import django

# Agregar el directorio raíz al path
sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube.models_adminet import TiendaNubeAdminetConfig, TiendaNubeCondVentaMap
from tiendanube.services.connection_service import MySQLConnectionService
from django.utils import timezone

def test_connection():
    """Probar conexión a administraNET"""
    print("🔍 Probando conexión a administraNET...")
    
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración activa de administraNET")
        return False
    
    print(f"✅ Configuración encontrada: {config.host}:{config.port}/{config.database}")
    
    try:
        mysql_config = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'user': config.user,
            'password': config.password,
        }
        
        mysql_service = MySQLConnectionService(mysql_config)
        result = mysql_service.test_connection(test_tables=False)
        
        if result.get('success'):
            print("✅ Conexión MySQL exitosa")
            return True
        else:
            print(f"❌ Error de conexión: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error probando conexión: {str(e)}")
        return False

def test_get_condiciones_venta():
    """Probar obtención de condiciones de venta"""
    print("\n🔍 Probando obtención de condiciones de venta...")
    
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración activa")
        return False
    
    try:
        mysql_config = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'user': config.user,
            'password': config.password,
        }
        
        mysql_service = MySQLConnectionService(mysql_config)
        
        # Probar diferentes queries para encontrar la tabla correcta
        queries = [
            "SELECT codigo, descripcion FROM cond_venta WHERE anulado = 'No' ORDER BY codigo LIMIT 5",
            "SELECT codigo, descripcion FROM cond_venta ORDER BY codigo LIMIT 5",
            "SHOW TABLES LIKE '%cond%'",
            "SHOW TABLES LIKE '%venta%'",
            "SHOW TABLES"
        ]
        
        for i, query in enumerate(queries):
            print(f"  Query {i+1}: {query}")
            try:
                result = mysql_service.execute_query(query)
                if result.get('success'):
                    results = result.get('results', [])
                    print(f"    ✅ Éxito: {len(results)} resultados")
                    if results:
                        for row in results[:3]:  # Mostrar solo los primeros 3
                            print(f"      {row}")
                    if 'cond_venta' in query and results:
                        print("    ✅ Tabla cond_venta encontrada y accesible")
                        return True
                else:
                    print(f"    ❌ Error: {result.get('error')}")
            except Exception as e:
                print(f"    ❌ Excepción: {str(e)}")
        
        return False
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return False

def test_mapping_operations():
    """Probar operaciones de mapeo"""
    print("\n🔍 Probando operaciones de mapeo...")
    
    # Crear un mapeo de prueba
    try:
        mapeo, created = TiendaNubeCondVentaMap.objects.get_or_create(
            adminet_codigo=999,
            defaults={
                'payment_method': 'TEST_PAYMENT_METHOD',
                'adminet_descripcion': 'Condición de prueba',
                'activo': True
            }
        )
        
        if created:
            print(f"✅ Mapeo de prueba creado: ID {mapeo.id}")
        else:
            print(f"✅ Mapeo de prueba existente: ID {mapeo.id}")
        
        # Actualizar el mapeo
        mapeo.payment_method = 'UPDATED_PAYMENT_METHOD'
        mapeo.activo = False
        mapeo.save()
        print("✅ Mapeo actualizado correctamente")
        
        # Verificar mapeos existentes
        total_mappings = TiendaNubeCondVentaMap.objects.count()
        active_mappings = TiendaNubeCondVentaMap.objects.filter(activo=True).count()
        print(f"📊 Total de mapeos: {total_mappings}")
        print(f"📊 Mapeos activos: {active_mappings}")
        
        # Eliminar mapeo de prueba
        mapeo.delete()
        print("✅ Mapeo de prueba eliminado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en operaciones de mapeo: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🧪 PRUEBA DE FUNCIONALIDAD DE MAPEO DE CONDICIONES DE VENTA")
    print(f"🕐 Fecha y hora: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Probar conexión
    connection_ok = test_connection()
    
    # Probar obtención de condiciones de venta
    if connection_ok:
        condiciones_ok = test_get_condiciones_venta()
    else:
        condiciones_ok = False
    
    # Probar operaciones de mapeo
    mapping_ok = test_mapping_operations()
    
    # Resumen
    print("\n" + "="*60)
    print(" RESUMEN DE PRUEBAS")
    print("="*60)
    print(f"🔗 Conexión MySQL: {'✅ OK' if connection_ok else '❌ FALLO'}")
    print(f"📋 Condiciones de venta: {'✅ OK' if condiciones_ok else '❌ FALLO'}")
    print(f"🗂️  Operaciones de mapeo: {'✅ OK' if mapping_ok else '❌ FALLO'}")
    
    if connection_ok and condiciones_ok and mapping_ok:
        print("\n🎉 TODAS LAS PRUEBAS PASARON")
        print("💡 La funcionalidad de mapeo está lista para usar")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")
        if not connection_ok:
            print("   - Verificar configuración de conexión MySQL")
        if not condiciones_ok:
            print("   - Verificar que la tabla cond_venta existe y es accesible")
        if not mapping_ok:
            print("   - Verificar permisos de base de datos")

if __name__ == "__main__":
    main() 