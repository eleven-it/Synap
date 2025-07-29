#!/usr/bin/env python3
"""
Script de prueba para el mapeo de clientes Tiendanube ↔ AdministraNET
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube.models_adminet import TiendaNubeClienteMap, TiendaNubeAdminetConfig
from tiendanube.services.connection_service import MySQLConnectionService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cliente_mapping():
    """Probar el mapeo de clientes"""
    print("🧪 PRUEBA DE MAPEO DE CLIENTES")
    print("=" * 50)
    
    # 1. Verificar configuración de administraNET
    print("\n1. Verificando configuración de administraNET...")
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    
    if not config:
        print("❌ No hay configuración activa de administraNET")
        return False
    
    print(f"✅ Configuración encontrada: {config.host}:{config.port}/{config.database}")
    
    # 2. Probar conexión a MySQL
    print("\n2. Probando conexión a MySQL...")
    try:
        mysql_config = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'user': config.user,
            'password': config.password,
        }
        
        mysql_service = MySQLConnectionService(mysql_config)
        result = mysql_service.test_connection()
        
        if result.get('success'):
            print("✅ Conexión MySQL exitosa")
        else:
            print(f"❌ Error de conexión MySQL: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error probando conexión: {str(e)}")
        return False
    
    # 3. Obtener clientes de administraNET
    print("\n3. Obteniendo clientes de administraNET...")
    try:
        query = """
            SELECT idcliente, nombre, email, documento
            FROM cliente 
            WHERE anulado = 'No' 
            ORDER BY nombre
            LIMIT 10
        """
        
        result = mysql_service.execute_query(query)
        
        if not result.get('success'):
            print(f"❌ Error obteniendo clientes: {result.get('error')}")
            return False
        
        clientes = result.get('results', [])
        print(f"✅ {len(clientes)} clientes encontrados")
        
        if clientes:
            print("\n📋 Primeros 5 clientes:")
            for i, cliente in enumerate(clientes[:5], 1):
                print(f"   {i}. ID: {cliente['idcliente']} - {cliente['nombre']} ({cliente.get('email', 'Sin email')})")
        
    except Exception as e:
        print(f"❌ Error obteniendo clientes: {str(e)}")
        return False
    
    # 4. Verificar mapeos existentes
    print("\n4. Verificando mapeos existentes...")
    mapeos = TiendaNubeClienteMap.objects.all()
    print(f"✅ {mapeos.count()} mapeos existentes")
    
    if mapeos.exists():
        print("\n📋 Mapeos actuales:")
        for mapeo in mapeos[:5]:
            print(f"   • {mapeo.tiendanube_email} → {mapeo.adminet_idcliente} ({mapeo.adminet_nombre})")
    
    # 5. Crear mapeo de prueba
    print("\n5. Creando mapeo de prueba...")
    try:
        if clientes:
            cliente_prueba = clientes[0]
            email_prueba = f"test.cliente.{cliente_prueba['idcliente']}@ejemplo.com"
            
            # Verificar si ya existe
            mapeo_existente = TiendaNubeClienteMap.objects.filter(
                adminet_idcliente=cliente_prueba['idcliente']
            ).first()
            
            if mapeo_existente:
                print(f"✅ Mapeo ya existe: {mapeo_existente.tiendanube_email} → {mapeo_existente.adminet_idcliente}")
            else:
                mapeo_prueba = TiendaNubeClienteMap.objects.create(
                    tiendanube_email=email_prueba,
                    adminet_idcliente=cliente_prueba['idcliente'],
                    adminet_nombre=cliente_prueba['nombre'],
                    adminet_documento=cliente_prueba.get('documento', ''),
                    activo=True
                )
                print(f"✅ Mapeo de prueba creado: {mapeo_prueba.tiendanube_email} → {mapeo_prueba.adminet_idcliente}")
        
    except Exception as e:
        print(f"❌ Error creando mapeo de prueba: {str(e)}")
        return False
    
    # 6. Probar búsqueda por mapeo
    print("\n6. Probando búsqueda por mapeo...")
    try:
        if clientes:
            cliente_prueba = clientes[0]
            mapeo = TiendaNubeClienteMap.objects.filter(
                adminet_idcliente=cliente_prueba['idcliente'],
                activo=True
            ).first()
            
            if mapeo:
                print(f"✅ Mapeo encontrado: {mapeo.tiendanube_email} → {mapeo.adminet_idcliente}")
            else:
                print("⚠️  No se encontró mapeo activo para el cliente de prueba")
        
    except Exception as e:
        print(f"❌ Error en búsqueda por mapeo: {str(e)}")
        return False
    
    print("\n✅ PRUEBA COMPLETADA EXITOSAMENTE")
    return True

def cleanup_test_data():
    """Limpiar datos de prueba"""
    print("\n🧹 Limpiando datos de prueba...")
    
    try:
        # Eliminar mapeos de prueba
        mapeos_prueba = TiendaNubeClienteMap.objects.filter(
            tiendanube_email__startswith='test.cliente.'
        )
        count = mapeos_prueba.count()
        mapeos_prueba.delete()
        print(f"✅ {count} mapeos de prueba eliminados")
        
    except Exception as e:
        print(f"❌ Error limpiando datos: {str(e)}")

if __name__ == '__main__':
    print("🚀 Iniciando pruebas de mapeo de clientes...")
    
    try:
        success = test_cliente_mapping()
        
        if success:
            print("\n🎉 Todas las pruebas pasaron correctamente!")
        else:
            print("\n💥 Algunas pruebas fallaron")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Pruebas interrumpidas por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {str(e)}")
        sys.exit(1)
    finally:
        # Preguntar si limpiar datos de prueba
        try:
            response = input("\n¿Deseas limpiar los datos de prueba? (y/N): ").strip().lower()
            if response in ['y', 'yes', 'sí', 'si']:
                cleanup_test_data()
        except:
            pass 