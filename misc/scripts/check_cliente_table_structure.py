#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla de clientes en administraNET
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from tiendanube.models_adminet import TiendaNubeAdminetConfig
from tiendanube.services.connection_service import MySQLConnectionService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_cliente_table_structure():
    """Verificar la estructura de la tabla de clientes"""
    print("🔍 VERIFICANDO ESTRUCTURA DE TABLA CLIENTES")
    print("=" * 60)
    
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
    
    # 3. Verificar si existe la tabla 'cliente' (singular)
    print("\n3. Verificando tabla 'cliente' (singular)...")
    try:
        query = "SHOW TABLES LIKE 'cliente'"
        result = mysql_service.execute_query(query)
        
        if result.get('success') and result.get('results'):
            print("✅ Tabla 'cliente' encontrada")
            table_name = 'cliente'
        else:
            print("❌ Tabla 'cliente' no encontrada")
            table_name = None
            
    except Exception as e:
        print(f"❌ Error verificando tabla 'cliente': {str(e)}")
        table_name = None
    
    # 4. Verificar si existe la tabla 'clientes' (plural)
    print("\n4. Verificando tabla 'clientes' (plural)...")
    try:
        query = "SHOW TABLES LIKE 'clientes'"
        result = mysql_service.execute_query(query)
        
        if result.get('success') and result.get('results'):
            print("✅ Tabla 'clientes' encontrada")
            if not table_name:
                table_name = 'clientes'
        else:
            print("❌ Tabla 'clientes' no encontrada")
            
    except Exception as e:
        print(f"❌ Error verificando tabla 'clientes': {str(e)}")
    
    if not table_name:
        print("❌ No se encontró ninguna tabla de clientes")
        return False
    
    print(f"\n📋 Usando tabla: '{table_name}'")
    
    # 5. Obtener estructura de la tabla
    print(f"\n5. Obteniendo estructura de la tabla '{table_name}'...")
    try:
        query = f"DESCRIBE {table_name}"
        result = mysql_service.execute_query(query)
        
        if result.get('success'):
            columns = result.get('results', [])
            print(f"✅ {len(columns)} columnas encontradas:")
            
            for col in columns:
                field_name = col.get('Field', '')
                field_type = col.get('Type', '')
                field_null = col.get('Null', '')
                field_key = col.get('Key', '')
                field_default = col.get('Default', '')
                
                key_info = ""
                if field_key == 'PRI':
                    key_info = " (PRIMARY KEY)"
                elif field_key == 'UNI':
                    key_info = " (UNIQUE)"
                
                print(f"   • {field_name}: {field_type} {field_null} {key_info}")
                if field_default:
                    print(f"     Default: {field_default}")
            
            # Buscar campos específicos
            field_names = [col.get('Field', '').lower() for col in columns]
            
            print(f"\n🔍 Búsqueda de campos específicos:")
            
            # Buscar campo de ID
            id_fields = [f for f in field_names if 'id' in f and 'cliente' in f]
            if id_fields:
                print(f"   ✅ Campos de ID encontrados: {id_fields}")
            else:
                print("   ❌ No se encontraron campos de ID específicos")
            
            # Buscar campo de código
            codigo_fields = [f for f in field_names if 'codigo' in f]
            if codigo_fields:
                print(f"   ✅ Campos de código encontrados: {codigo_fields}")
            else:
                print("   ❌ No se encontraron campos de código")
            
            # Buscar campo de nombre
            nombre_fields = [f for f in field_names if 'nombre' in f]
            if nombre_fields:
                print(f"   ✅ Campos de nombre encontrados: {nombre_fields}")
            else:
                print("   ❌ No se encontraron campos de nombre")
            
            # Buscar campo de email
            email_fields = [f for f in field_names if 'email' in f]
            if email_fields:
                print(f"   ✅ Campos de email encontrados: {email_fields}")
            else:
                print("   ❌ No se encontraron campos de email")
            
            # Buscar campo de documento
            doc_fields = [f for f in field_names if 'documento' in f or 'cuit' in f or 'dni' in f]
            if doc_fields:
                print(f"   ✅ Campos de documento encontrados: {doc_fields}")
            else:
                print("   ❌ No se encontraron campos de documento")
            
        else:
            print(f"❌ Error obteniendo estructura: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error obteniendo estructura: {str(e)}")
        return False
    
    # 6. Obtener algunos registros de ejemplo
    print(f"\n6. Obteniendo registros de ejemplo de '{table_name}'...")
    try:
        # Intentar con diferentes campos de ID
        possible_id_fields = ['idcliente', 'codigo', 'id', 'codigo_cliente']
        
        for id_field in possible_id_fields:
            if id_field in field_names:
                query = f"SELECT {id_field}, nombre, email, documento FROM {table_name} WHERE anulado = 'No' LIMIT 5"
                result = mysql_service.execute_query(query)
                
                if result.get('success'):
                    records = result.get('results', [])
                    print(f"✅ Usando campo '{id_field}' - {len(records)} registros encontrados:")
                    
                    for i, record in enumerate(records, 1):
                        print(f"   {i}. {id_field}: {record.get(id_field)} - {record.get('nombre', 'Sin nombre')}")
                    
                    # Guardar información para el código
                    print(f"\n📝 INFORMACIÓN PARA EL CÓDIGO:")
                    print(f"   Tabla: '{table_name}'")
                    print(f"   Campo ID: '{id_field}'")
                    print(f"   Campo nombre: 'nombre'")
                    print(f"   Campo email: 'email'")
                    print(f"   Campo documento: 'documento'")
                    
                    break
                else:
                    print(f"   ❌ Error con campo '{id_field}': {result.get('error')}")
        else:
            print("❌ No se pudo obtener registros con ningún campo de ID")
            
    except Exception as e:
        print(f"❌ Error obteniendo registros: {str(e)}")
        return False
    
    print("\n✅ VERIFICACIÓN COMPLETADA")
    return True

if __name__ == '__main__':
    print("🚀 Iniciando verificación de estructura de tabla clientes...")
    
    try:
        success = check_cliente_table_structure()
        
        if success:
            print("\n🎉 Verificación completada exitosamente!")
        else:
            print("\n💥 La verificación falló")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Verificación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {str(e)}")
        sys.exit(1) 