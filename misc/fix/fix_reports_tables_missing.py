#!/usr/bin/env python
"""
Script para corregir cuando reports.0001_initial está marcada como aplicada
pero las tablas no existen realmente en la base de datos.
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.db import connection

def check_table_exists(table_name):
    """Verifica si una tabla existe en la base de datos"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, [table_name])
        return cursor.fetchone()[0]

def fix_reports_tables():
    """Corrige el problema de tablas faltantes de reports"""
    # Tablas que deberían existir después de reports.0001_initial
    required_tables = [
        'reports_reportdefinition',
        'reports_reportwidget',
        'reports_reportexecutionlog',
        'reports_reportdashboard',
    ]
    
    print("🔍 Verificando existencia de tablas de reports...")
    missing_tables = []
    for table in required_tables:
        exists = check_table_exists(table)
        status = "✅" if exists else "❌"
        print(f"  {status} {table}: {'existe' if exists else 'NO existe'}")
        if not exists:
            missing_tables.append(table)
    
    if not missing_tables:
        print("\n✅ Todas las tablas de reports existen. No se requiere corrección.")
        return True
    
    print(f"\n⚠️  Faltan {len(missing_tables)} tablas de reports.")
    print("   Esto indica que reports.0001_initial está marcada como aplicada pero no se ejecutó realmente.")
    
    # Verificar si la migración está marcada como aplicada
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM django_migrations 
            WHERE app = 'reports' AND name = '0001_initial';
        """)
        migration_exists = cursor.fetchone()[0] > 0
        
        if migration_exists:
            print("\n📝 Deshaciendo reports.0001_initial de la tabla de migraciones...")
            cursor.execute("""
                DELETE FROM django_migrations 
                WHERE app = 'reports' AND name = '0001_initial';
            """)
            connection.commit()
            print("✅ Migración reports.0001_initial eliminada de django_migrations")
            print("\n💡 Ahora puedes ejecutar:")
            print("   sudo docker exec Synap_app python manage.py migrate reports 0001_initial")
            print("   sudo docker exec Synap_app python manage.py migrate")
            return True
        else:
            print("\n⚠️  La migración reports.0001_initial no está en django_migrations.")
            print("   Esto es correcto. Solo necesitas aplicar las migraciones:")
            print("   sudo docker exec Synap_app python manage.py migrate")
            return True

if __name__ == '__main__':
    try:
        success = fix_reports_tables()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

