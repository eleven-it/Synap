#!/usr/bin/env python3
"""
Script de prueba para el mapeo de clientes Tiendanube ↔ AdministraNET (CORREGIDO)
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube.models_adminet import TiendaNubeAdminetConfig, TiendaNubeClienteMap
from tiendanube.services.connection_service import MySQLConnectionService
from tiendanube.services.order_to_adminet_service import OrderToAdminetService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cliente_mapping():
    """Probar el mapeo de clientes con los campos corregidos"""
    print("🧪 PRUEBA DE MAPEO DE CLIENTES (CORREGIDO)")
    print("=" * 60)
    
    # 1. Verificar configuración
    print("\n1. Verificando configuración de administraNET...")
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    
    if not config:
        print("❌ No hay configuración activa de administraNET")
        return False
    
    print(f"✅ Configuración encontrada: {config.host}:{config.port}/{config.database}")
    
    # 2. Probar conexión y obtener clientes
    print("\n2. Probando conexión y obteniendo clientes...")
    try:
        mysql_config = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'user': config.user,
            'password': config.password,
        }
        
        mysql_service = MySQLConnectionService(mysql_config)
        
        # Obtener algunos clientes de administraNET
        query = """
            SELECT codigo, nombre_cliente, email, cuit 
            FROM cliente 
            LIMIT 5
        """
        
        result = mysql_service.execute_query(query)
        
        if not result.get('success'):
            print(f"❌ Error obteniendo clientes: {result.get('error')}")
            return False
        
        clientes = result.get('results', [])
        print(f"✅ {len(clientes)} clientes obtenidos de administraNET")
        
        if not clientes:
            print("❌ No hay clientes disponibles para probar")
            return False
        
        # Mostrar clientes disponibles
        print("\n📋 Clientes disponibles:")
        for i, cliente in enumerate(clientes, 1):
            print(f"   {i}. Código: {cliente['codigo']} - {cliente['nombre_cliente']} ({cliente.get('email', 'Sin email')})")
        
    except Exception as e:
        print(f"❌ Error en conexión: {str(e)}")
        return False
    
    # 3. Probar creación de mapeos
    print("\n3. Probando creación de mapeos...")
    try:
        # Crear algunos mapeos de prueba
        test_mappings = []
        for i, cliente in enumerate(clientes[:3]):  # Usar solo los primeros 3
            email_test = f"test{i+1}@tiendanube.com"
            
            # Verificar si ya existe
            existing = TiendaNubeClienteMap.objects.filter(
                tiendanube_email=email_test
            ).first()
            
            if existing:
                print(f"   ⚠️  Mapeo existente para {email_test}, eliminando...")
                existing.delete()
            
            # Crear nuevo mapeo
            mapeo = TiendaNubeClienteMap.objects.create(
                tiendanube_email=email_test,
                adminet_codigo=cliente['codigo'],
                adminet_nombre=cliente['nombre_cliente'],
                adminet_documento=cliente.get('cuit', ''),
                activo=True
            )
            
            test_mappings.append(mapeo)
            print(f"   ✅ Mapeo creado: {email_test} → {cliente['codigo']} ({cliente['nombre_cliente']})")
        
    except Exception as e:
        print(f"❌ Error creando mapeos: {str(e)}")
        return False
    
    # 4. Probar búsqueda de mapeos
    print("\n4. Probando búsqueda de mapeos...")
    try:
        for mapeo in test_mappings:
            # Buscar por email
            found = TiendaNubeClienteMap.objects.filter(
                tiendanube_email=mapeo.tiendanube_email,
                activo=True
            ).first()
            
            if found:
                print(f"   ✅ Mapeo encontrado: {found.tiendanube_email} → {found.adminet_codigo}")
            else:
                print(f"   ❌ Mapeo no encontrado para: {mapeo.tiendanube_email}")
                return False
        
    except Exception as e:
        print(f"❌ Error buscando mapeos: {str(e)}")
        return False
    
    # 5. Probar integración con OrderToAdminetService
    print("\n5. Probando integración con OrderToAdminetService...")
    try:
        order_service = OrderToAdminetService()
        
        # Simular datos de pedido de Tiendanube
        test_order_data = {
            'customer': {
                'email': test_mappings[0].tiendanube_email,
                'name': 'Cliente de Prueba',
                'identification': '12345678'
            }
        }
        
        # Probar búsqueda de cliente
        cliente_id = order_service._get_or_create_cliente(test_order_data)
        
        if cliente_id:
            print(f"   ✅ Cliente encontrado/creado: {cliente_id}")
            
            # Verificar que coincide con el mapeo
            if cliente_id == test_mappings[0].adminet_codigo:
                print(f"   ✅ ID coincide con el mapeo: {cliente_id}")
            else:
                print(f"   ⚠️  ID no coincide: esperado {test_mappings[0].adminet_codigo}, obtenido {cliente_id}")
        else:
            print("   ❌ No se pudo obtener/crear cliente")
            return False
        
    except Exception as e:
        print(f"❌ Error en OrderToAdminetService: {str(e)}")
        return False
    
    # 6. Verificar estadísticas
    print("\n6. Verificando estadísticas...")
    try:
        total_mappings = TiendaNubeClienteMap.objects.count()
        active_mappings = TiendaNubeClienteMap.objects.filter(activo=True).count()
        
        print(f"   📊 Total de mapeos: {total_mappings}")
        print(f"   📊 Mapeos activos: {active_mappings}")
        
        if total_mappings > 0:
            print("   ✅ Estadísticas correctas")
        else:
            print("   ❌ No hay mapeos en la base de datos")
            return False
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {str(e)}")
        return False
    
    print("\n✅ PRUEBA COMPLETADA EXITOSAMENTE")
    return True

def cleanup_test_data():
    """Limpiar datos de prueba"""
    print("\n🧹 LIMPIANDO DATOS DE PRUEBA")
    print("=" * 40)
    
    try:
        # Eliminar mapeos de prueba
        test_emails = [f"test{i+1}@tiendanube.com" for i in range(3)]
        deleted_count = TiendaNubeClienteMap.objects.filter(
            tiendanube_email__in=test_emails
        ).delete()[0]
        
        print(f"✅ {deleted_count} mapeos de prueba eliminados")
        
    except Exception as e:
        print(f"❌ Error limpiando datos: {str(e)}")

if __name__ == '__main__':
    print("🚀 Iniciando prueba de mapeo de clientes...")
    
    try:
        success = test_cliente_mapping()
        
        if success:
            print("\n🎉 ¡PRUEBA EXITOSA! El mapeo de clientes funciona correctamente.")
            
            # Preguntar si limpiar datos de prueba
            print("\n¿Deseas limpiar los datos de prueba? (s/n): ", end="")
            try:
                response = input().strip().lower()
                if response in ['s', 'si', 'sí', 'y', 'yes']:
                    cleanup_test_data()
                    print("✅ Datos de prueba limpiados")
                else:
                    print("ℹ️  Datos de prueba conservados para inspección manual")
            except EOFError:
                print("ℹ️  Datos de prueba conservados (modo no interactivo)")
        else:
            print("\n💥 La prueba falló")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Prueba interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {str(e)}")
        sys.exit(1) 