#!/usr/bin/env python3
"""
Script para verificar la conexión a la base de datos administraNET
"""

import os
import sys
import django
from django.conf import settings
from django.db import connections, DatabaseError
from django.core.management import execute_from_command_line

# Colores para output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def print_colored(message, color=Colors.NC):
    """Imprimir mensaje con color"""
    print(f"{color}{message}{Colors.NC}")

def setup_django():
    """Configurar Django"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
        django.setup()
        return True
    except Exception as e:
        print_colored(f"❌ Error configurando Django: {e}", Colors.RED)
        return False

def test_mysql_connection():
    """Verificar conexión básica a MySQL"""
    try:
        with connections['mysql'].cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print_colored(f"✅ Conexión exitosa a MySQL", Colors.GREEN)
            print_colored(f"   Versión: {version[0]}", Colors.CYAN)
            return True
    except Exception as e:
        print_colored(f"❌ Error de conexión MySQL: {e}", Colors.RED)
        return False

def check_administraNET_tables():
    """Verificar tablas principales de administraNET"""
    tables_to_check = [
        'stock',
        'stock_deposito', 
        'articulos',
        'depositos',
        'clientes',
        'proveedores',
        'lote',
        'lote_stock',
        'pedidos',
        'pedidos_detalle'
    ]
    
    found_tables = []
    missing_tables = []
    
    try:
        with connections['mysql'].cursor() as cursor:
            for table in tables_to_check:
                cursor.execute("SHOW TABLES LIKE %s", [table])
                if cursor.fetchone():
                    # Contar registros
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    count = cursor.fetchone()[0]
                    found_tables.append((table, count))
                else:
                    missing_tables.append(table)
        
        # Mostrar resultados
        if found_tables:
            print_colored("\n📋 Tablas encontradas:", Colors.BLUE)
            for table, count in found_tables:
                print_colored(f"   ✅ {table}: {count:,} registros", Colors.GREEN)
        
        if missing_tables:
            print_colored("\n⚠️  Tablas no encontradas:", Colors.YELLOW)
            for table in missing_tables:
                print_colored(f"   ❌ {table}", Colors.RED)
        
        return len(found_tables) > 0
        
    except Exception as e:
        print_colored(f"❌ Error verificando tablas: {e}", Colors.RED)
        return False

def check_database_info():
    """Obtener información general de la base de datos"""
    try:
        with connections['mysql'].cursor() as cursor:
            # Obtener nombre de la base de datos
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print_colored(f"\n🗄️  Base de datos: {db_name}", Colors.PURPLE)
            
            # Obtener todas las tablas
            cursor.execute("SHOW TABLES")
            all_tables = [row[0] for row in cursor.fetchall()]
            print_colored(f"   Total de tablas: {len(all_tables)}", Colors.CYAN)
            
            # Obtener tamaño aproximado de la base de datos
            cursor.execute("""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size in MB'
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
            """)
            db_size = cursor.fetchone()[0]
            print_colored(f"   Tamaño aproximado: {db_size} MB", Colors.CYAN)
            
            return True
            
    except Exception as e:
        print_colored(f"❌ Error obteniendo información de BD: {e}", Colors.RED)
        return False

def test_sample_queries():
    """Probar consultas de ejemplo"""
    print_colored("\n🔍 Probando consultas de ejemplo:", Colors.BLUE)
    
    queries = [
        ("Artículos totales", "SELECT COUNT(*) FROM articulos"),
        ("Depósitos disponibles", "SELECT COUNT(*) FROM depositos"),
        ("Stock total", "SELECT COUNT(*) FROM stock"),
        ("Stock por depósito", "SELECT COUNT(*) FROM stock_deposito"),
        ("Clientes activos", "SELECT COUNT(*) FROM clientes"),
        ("Proveedores", "SELECT COUNT(*) FROM proveedores"),
    ]
    
    try:
        with connections['mysql'].cursor() as cursor:
            for description, query in queries:
                try:
                    cursor.execute(query)
                    result = cursor.fetchone()[0]
                    print_colored(f"   ✅ {description}: {result:,}", Colors.GREEN)
                except Exception as e:
                    print_colored(f"   ❌ {description}: Error - {str(e)[:50]}...", Colors.RED)
                    
    except Exception as e:
        print_colored(f"❌ Error en consultas de ejemplo: {e}", Colors.RED)

def check_connection_settings():
    """Verificar configuración de conexión"""
    print_colored("\n⚙️  Configuración de conexión:", Colors.BLUE)
    
    db_settings = settings.DATABASES.get('mysql', {})
    
    print_colored(f"   Host: {db_settings.get('HOST', 'N/A')}", Colors.CYAN)
    print_colored(f"   Puerto: {db_settings.get('PORT', 'N/A')}", Colors.CYAN)
    print_colored(f"   Base de datos: {db_settings.get('NAME', 'N/A')}", Colors.CYAN)
    print_colored(f"   Usuario: {db_settings.get('USER', 'N/A')}", Colors.CYAN)
    print_colored(f"   Motor: {db_settings.get('ENGINE', 'N/A')}", Colors.CYAN)

def main():
    """Función principal"""
    print_colored("🔧 Verificador de Conexión administraNET", Colors.PURPLE)
    print_colored("=" * 50, Colors.PURPLE)
    
    # Configurar Django
    if not setup_django():
        sys.exit(1)
    
    # Verificar configuración
    check_connection_settings()
    
    # Probar conexión MySQL
    if not test_mysql_connection():
        sys.exit(1)
    
    # Verificar información de la base de datos
    check_database_info()
    
    # Verificar tablas principales
    if not check_administraNET_tables():
        print_colored("\n⚠️  No se encontraron tablas principales de administraNET", Colors.YELLOW)
        print_colored("   Verifica que la base de datos sea correcta", Colors.YELLOW)
    
    # Probar consultas de ejemplo
    test_sample_queries()
    
    print_colored("\n" + "=" * 50, Colors.PURPLE)
    print_colored("✅ Verificación completada", Colors.GREEN)

if __name__ == "__main__":
    main() 