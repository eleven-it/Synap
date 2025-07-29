#!/usr/bin/env python3
"""
Script simple para verificar la estructura de la tabla cliente
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

def check_cliente_structure():
    """Verificar la estructura real de la tabla cliente"""
    print("🔍 VERIFICANDO ESTRUCTURA DE TABLA CLIENTE")
    print("=" * 50)
    
    # 1. Obtener configuración
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración activa")
        return
    
    print(f"✅ Configuración: {config.host}:{config.port}/{config.database}")
    
    # 2. Conectar y verificar estructura
    try:
        mysql_config = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'user': config.user,
            'password': config.password,
        }
        
        mysql_service = MySQLConnectionService(mysql_config)
        
        # Verificar si existe la tabla
        print("\n1. Verificando existencia de tabla 'cliente'...")
        result = mysql_service.execute_query("SHOW TABLES LIKE 'cliente'")
        if result.get('success') and result.get('results'):
            print("✅ Tabla 'cliente' existe")
        else:
            print("❌ Tabla 'cliente' no existe")
            return
        
        # Obtener estructura
        print("\n2. Obteniendo estructura de la tabla...")
        result = mysql_service.execute_query("DESCRIBE cliente")
        if result.get('success'):
            columns = result.get('results', [])
            print(f"✅ {len(columns)} columnas encontradas:")
            
            for col in columns:
                field_name = col.get('Field', '')
                field_type = col.get('Type', '')
                field_key = col.get('Key', '')
                
                key_info = ""
                if field_key == 'PRI':
                    key_info = " (PRIMARY KEY)"
                elif field_key == 'UNI':
                    key_info = " (UNIQUE)"
                
                print(f"   • {field_name}: {field_type}{key_info}")
            
            # Buscar campos específicos
            field_names = [col.get('Field', '').lower() for col in columns]
            
            print(f"\n3. Búsqueda de campos específicos:")
            
            # Buscar campo de ID/código
            id_fields = [f for f in field_names if any(x in f for x in ['id', 'codigo', 'cliente'])]
            if id_fields:
                print(f"   ✅ Campos de ID encontrados: {id_fields}")
            else:
                print("   ❌ No se encontraron campos de ID")
            
            # Buscar campo de nombre
            nombre_fields = [f for f in field_names if 'nombre' in f or 'name' in f]
            if nombre_fields:
                print(f"   ✅ Campos de nombre encontrados: {nombre_fields}")
            else:
                print("   ❌ No se encontraron campos de nombre")
            
            # Buscar campo de email
            email_fields = [f for f in field_names if 'email' in f or 'mail' in f]
            if email_fields:
                print(f"   ✅ Campos de email encontrados: {email_fields}")
            else:
                print("   ❌ No se encontraron campos de email")
            
            # Buscar campo de documento
            doc_fields = [f for f in field_names if any(x in f for x in ['documento', 'cuit', 'dni', 'doc'])]
            if doc_fields:
                print(f"   ✅ Campos de documento encontrados: {doc_fields}")
            else:
                print("   ❌ No se encontraron campos de documento")
            
            # 4. Obtener algunos registros de ejemplo
            print(f"\n4. Obteniendo registros de ejemplo...")
            
            # Intentar con diferentes campos de ID
            possible_id_fields = ['codigo', 'idcliente', 'id', 'codigo_cliente']
            
            for id_field in possible_id_fields:
                if id_field in field_names:
                    # Intentar obtener algunos registros
                    query = f"SELECT {id_field} FROM cliente LIMIT 3"
                    result = mysql_service.execute_query(query)
                    
                    if result.get('success'):
                        records = result.get('results', [])
                        if records:
                            print(f"   ✅ Campo '{id_field}' funciona - {len(records)} registros obtenidos")
                            
                            # Mostrar el primer registro completo
                            first_id = records[0].get(id_field)
                            if first_id:
                                full_query = f"SELECT * FROM cliente WHERE {id_field} = {first_id}"
                                full_result = mysql_service.execute_query(full_query)
                                
                                if full_result.get('success') and full_result.get('results'):
                                    first_record = full_result['results'][0]
                                    print(f"   📋 Primer registro completo:")
                                    for key, value in first_record.items():
                                        print(f"      {key}: {value}")
                                break
                        else:
                            print(f"   ⚠️  Campo '{id_field}' funciona pero no hay registros")
                    else:
                        print(f"   ❌ Error con campo '{id_field}': {result.get('error')}")
            else:
                print("   ❌ No se pudo obtener registros con ningún campo de ID")
        
        else:
            print(f"❌ Error obteniendo estructura: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    check_cliente_structure() 