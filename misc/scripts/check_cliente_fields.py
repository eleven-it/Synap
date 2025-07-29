#!/usr/bin/env python3
"""
Script para verificar exactamente qué campos existen en la tabla cliente
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

def check_cliente_fields():
    """Verificar exactamente qué campos existen en la tabla cliente"""
    print("🔍 VERIFICANDO CAMPOS DE TABLA CLIENTE")
    print("=" * 50)
    
    # 1. Obtener configuración
    config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración activa")
        return
    
    print(f"✅ Configuración: {config.host}:{config.port}/{config.database}")
    
    # 2. Conectar y verificar campos
    try:
        mysql_config = {
            'host': config.host,
            'port': config.port,
            'database': config.database,
            'user': config.user,
            'password': config.password,
        }
        
        mysql_service = MySQLConnectionService(mysql_config)
        
        # Obtener estructura completa
        print("\n1. Obteniendo estructura completa de la tabla 'cliente'...")
        result = mysql_service.execute_query("DESCRIBE cliente")
        
        if result.get('success'):
            columns = result.get('results', [])
            print(f"✅ {len(columns)} columnas encontradas:")
            
            field_names = []
            for col in columns:
                field_name = col.get('Field', '')
                field_type = col.get('Type', '')
                field_null = col.get('Null', '')
                field_key = col.get('Key', '')
                field_default = col.get('Default', '')
                
                field_names.append(field_name.lower())
                
                key_info = ""
                if field_key == 'PRI':
                    key_info = " (PRIMARY KEY)"
                elif field_key == 'UNI':
                    key_info = " (UNIQUE)"
                
                print(f"   • {field_name}: {field_type} {field_null}{key_info}")
                if field_default:
                    print(f"     Default: {field_default}")
            
            # Buscar campos específicos que necesitamos
            print(f"\n2. Búsqueda de campos específicos:")
            
            # Campos que necesitamos para el mapeo
            needed_fields = {
                'id/codigo': ['codigo', 'idcliente', 'id', 'codigo_cliente'],
                'nombre': ['nombre_cliente', 'nombre', 'name', 'cliente'],
                'email': ['email', 'mail', 'correo'],
                'documento': ['cuit', 'documento', 'dni', 'doc'],
                'telefono': ['telefono', 'phone', 'tel'],
                'direccion': ['direccion', 'address', 'domicilio'],
                'ciudad': ['localidad', 'ciudad', 'city'],
                'provincia': ['provincia', 'state', 'estado'],
                'codigo_postal': ['codigopostal', 'postal', 'cp']
            }
            
            available_fields = {}
            for category, possible_names in needed_fields.items():
                found = [f for f in field_names if f in possible_names]
                if found:
                    available_fields[category] = found[0]  # Tomar el primero encontrado
                    print(f"   ✅ {category}: {found[0]}")
                else:
                    print(f"   ❌ {category}: No encontrado")
            
            # 3. Probar consulta con campos disponibles
            print(f"\n3. Probando consulta con campos disponibles...")
            
            if 'id/codigo' in available_fields and 'nombre' in available_fields:
                id_field = available_fields['id/codigo']
                nombre_field = available_fields['nombre']
                
                # Construir consulta con campos disponibles
                select_fields = [id_field, nombre_field]
                
                if 'email' in available_fields:
                    select_fields.append(available_fields['email'])
                if 'documento' in available_fields:
                    select_fields.append(available_fields['documento'])
                if 'telefono' in available_fields:
                    select_fields.append(available_fields['telefono'])
                if 'direccion' in available_fields:
                    select_fields.append(available_fields['direccion'])
                if 'ciudad' in available_fields:
                    select_fields.append(available_fields['ciudad'])
                if 'provincia' in available_fields:
                    select_fields.append(available_fields['provincia'])
                
                query = f"SELECT {', '.join(select_fields)} FROM cliente LIMIT 3"
                print(f"   🔍 Consulta: {query}")
                
                result = mysql_service.execute_query(query)
                if result.get('success'):
                    records = result.get('results', [])
                    print(f"   ✅ {len(records)} registros obtenidos")
                    
                    if records:
                        print(f"   📋 Primer registro:")
                        for key, value in records[0].items():
                            print(f"      {key}: {value}")
                        
                        # Mostrar información para el código
                        print(f"\n📝 INFORMACIÓN PARA EL CÓDIGO:")
                        print(f"   Campos disponibles: {available_fields}")
                        print(f"   Consulta recomendada: {query}")
                        
                else:
                    print(f"   ❌ Error en consulta: {result.get('error')}")
            else:
                print("   ❌ No se encontraron campos mínimos necesarios (id y nombre)")
        
        else:
            print(f"❌ Error obteniendo estructura: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    check_cliente_fields() 