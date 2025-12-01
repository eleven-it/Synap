#!/usr/bin/env python
"""
Script para corregir el orden de migraciones en la base de datos.
Resuelve el problema cuando reports.0001_initial está aplicada antes que core.0007_increase_permiso_codigo_length
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.db import connection
from django.utils import timezone

def fix_migration_order():
    """Corrige el orden de las migraciones en la base de datos"""
    with connection.cursor() as cursor:
        # 1. Verificar el estado actual
        cursor.execute("""
            SELECT app, name, applied 
            FROM django_migrations 
            WHERE app IN ('core', 'reports') 
            AND name IN ('0007_increase_permiso_codigo_length', '0001_initial')
            ORDER BY applied;
        """)
        current = cursor.fetchall()
        print("Estado actual de las migraciones:")
        for row in current:
            print(f"  {row[0]}.{row[1]}: aplicada en {row[2]}")
        
        # 2. Obtener la fecha de aplicación de core.0006 (anterior a 0007)
        cursor.execute("""
            SELECT applied 
            FROM django_migrations 
            WHERE app = 'core' AND name = '0006_empresa_country_alter_empresa_logo_and_more'
            ORDER BY applied DESC 
            LIMIT 1;
        """)
        core_0006_result = cursor.fetchone()
        
        if not core_0006_result:
            print("❌ Error: No se encontró la migración core.0006")
            return False
        
        core_0006_date = core_0006_result[0]
        print(f"\nFecha de core.0006: {core_0006_date}")
        
        # 3. Obtener la fecha de aplicación de reports.0001
        cursor.execute("""
            SELECT applied 
            FROM django_migrations 
            WHERE app = 'reports' AND name = '0001_initial'
            ORDER BY applied DESC 
            LIMIT 1;
        """)
        reports_0001_result = cursor.fetchone()
        
        if not reports_0001_result:
            print("❌ Error: No se encontró la migración reports.0001_initial")
            return False
        
        reports_0001_date = reports_0001_result[0]
        print(f"Fecha de reports.0001: {reports_0001_date}")
        
        # 4. Calcular nueva fecha para core.0007 (entre 0006 y reports.0001)
        # Usar una fecha ligeramente anterior a reports.0001
        from datetime import timedelta
        new_core_0007_date = reports_0001_date - timedelta(seconds=1)
        
        # 5. Verificar si core.0007 ya existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM django_migrations 
            WHERE app = 'core' AND name = '0007_increase_permiso_codigo_length';
        """)
        core_0007_exists = cursor.fetchone()[0] > 0
        
        if core_0007_exists:
            # Actualizar la fecha de core.0007
            print(f"\n📝 Actualizando fecha de core.0007_increase_permiso_codigo_length a {new_core_0007_date}")
            cursor.execute("""
                UPDATE django_migrations 
                SET applied = %s 
                WHERE app = 'core' AND name = '0007_increase_permiso_codigo_length';
            """, [new_core_0007_date])
        else:
            # Insertar core.0007 con la fecha correcta
            print(f"\n➕ Insertando core.0007_increase_permiso_codigo_length con fecha {new_core_0007_date}")
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied)
                VALUES ('core', '0007_increase_permiso_codigo_length', %s);
            """, [new_core_0007_date])
        
        connection.commit()
        print("✅ Orden de migraciones corregido exitosamente")
        
        # 6. Verificar el nuevo estado
        cursor.execute("""
            SELECT app, name, applied 
            FROM django_migrations 
            WHERE app IN ('core', 'reports') 
            AND name IN ('0007_increase_permiso_codigo_length', '0001_initial')
            ORDER BY applied;
        """)
        new_state = cursor.fetchall()
        print("\nNuevo estado de las migraciones:")
        for row in new_state:
            print(f"  {row[0]}.{row[1]}: aplicada en {row[2]}")
        
        return True

if __name__ == '__main__':
    try:
        success = fix_migration_order()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

