#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla cliente usando Django
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.append('/app')
django.setup()

from django.db import connections
from tiendanube.models_adminet import TiendaNubeAdminetConfig

def check_cliente_structure():
    """Verificar la estructura real de la tabla cliente usando Django"""
    print("🔍 VERIFICANDO ESTRUCTURA DE TABLA CLIENTE (DJANGO)")
    print("=" * 60)
    
    # 1. Obtener configuración
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración activa")
        return
    
    print(f"✅ Configuración: {config.host}:{config.port}/{config.database}")
    
    # 2. Usar conexión Django
    try:
        with connections['mysql'].cursor() as cursor:
            # Verificar si existe la tabla
            print("\n1. Verificando existencia de tabla 'cliente'...")
            cursor.execute("SHOW TABLES LIKE 'cliente'")
            if cursor.fetchone():
                print("✅ Tabla 'cliente' existe")
            else:
                print("❌ Tabla 'cliente' no existe")
                return
            
            # Obtener estructura
            print("\n2. Obteniendo estructura de la tabla...")
            cursor.execute("DESCRIBE cliente")
            columns = cursor.fetchall()
            print(f"✅ {len(columns)} columnas encontradas:")
            
            field_names = []
            for col in columns:
                field_name = col[0]  # Field name
                field_type = col[1]  # Type
                field_null = col[2]  # Null
                field_key = col[3]   # Key
                field_default = col[4]  # Default
                
                field_names.append(field_name.lower())
                
                key_info = ""
                if field_key == 'PRI':
                    key_info = " (PRIMARY KEY)"
                elif field_key == 'UNI':
                    key_info = " (UNIQUE)"
                
                print(f"   • {field_name}: {field_type} {field_null}{key_info}")
                if field_default:
                    print(f"     Default: {field_default}")
            
            # Buscar campos específicos
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
                    cursor.execute(f"SELECT {id_field} FROM cliente LIMIT 3")
                    records = cursor.fetchall()
                    
                    if records:
                        print(f"   ✅ Campo '{id_field}' funciona - {len(records)} registros obtenidos")
                        
                        # Mostrar el primer registro completo
                        first_id = records[0][0]
                        if first_id:
                            cursor.execute(f"SELECT * FROM cliente WHERE {id_field} = %s", [first_id])
                            full_record = cursor.fetchone()
                            
                            if full_record:
                                print(f"   📋 Primer registro completo:")
                                # Obtener nombres de columnas
                                cursor.execute("DESCRIBE cliente")
                                column_names = [col[0] for col in cursor.fetchall()]
                                
                                for i, value in enumerate(full_record):
                                    if i < len(column_names):
                                        print(f"      {column_names[i]}: {value}")
                            break
                    else:
                        print(f"   ⚠️  Campo '{id_field}' funciona pero no hay registros")
            else:
                print("   ❌ No se pudo obtener registros con ningún campo de ID")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    check_cliente_structure() 