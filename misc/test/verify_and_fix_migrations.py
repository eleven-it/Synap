#!/usr/bin/env python
"""
Script para verificar y aplicar migraciones pendientes
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.core.management import execute_from_command_line
from core.models import Empresa, Country, State, FiscalResponsibility
from core.models.currency import Currency

def verify_migrations():
    """Verifica el estado de las migraciones"""
    print("🔍 Verificando estado de migraciones...")
    
    # Verificar que los campos existen
    try:
        empresa = Empresa._meta.get_field('country')
        print("✅ Campo 'country' existe en modelo Empresa")
    except Exception as e:
        print(f"❌ Campo 'country' no existe: {e}")
        return False
    
    try:
        empresa = Empresa._meta.get_field('state')
        print("✅ Campo 'state' existe en modelo Empresa")
    except Exception as e:
        print(f"❌ Campo 'state' no existe: {e}")
        return False
    
    try:
        empresa = Empresa._meta.get_field('fiscal_responsibility')
        print("✅ Campo 'fiscal_responsibility' existe en modelo Empresa")
    except Exception as e:
        print(f"❌ Campo 'fiscal_responsibility' no existe: {e}")
        return False
    
    return True

def verify_data():
    """Verifica que hay datos de prueba disponibles"""
    print("\n📊 Verificando datos de prueba...")
    
    country = Country.objects.filter(name__icontains='argentina').first()
    state = State.objects.filter(name__icontains='mendoza').first()
    fiscal_responsibility = FiscalResponsibility.objects.filter(name__icontains='inscripto').first()
    currency = Currency.objects.filter(name__icontains='peso').first()
    
    print(f"   - País Argentina: {'✅' if country else '❌'} (ID: {country.id if country else 'N/A'})")
    print(f"   - Provincia Mendoza: {'✅' if state else '❌'} (ID: {state.id if state else 'N/A'})")
    print(f"   - Responsabilidad Inscripto: {'✅' if fiscal_responsibility else '❌'} (ID: {fiscal_responsibility.id if fiscal_responsibility else 'N/A'})")
    print(f"   - Moneda Peso: {'✅' if currency else '❌'} (ID: {currency.id if currency else 'N/A'})")
    
    if not all([country, state, fiscal_responsibility, currency]):
        print("\n⚠️  Faltan datos de prueba. Ejecutando comandos de población...")
        return False
    
    return True

def run_migrations():
    """Ejecuta las migraciones pendientes"""
    print("\n🔄 Ejecutando migraciones...")
    
    try:
        # Ejecutar makemigrations
        print("   - Ejecutando makemigrations...")
        execute_from_command_line(['manage.py', 'makemigrations'])
        
        # Ejecutar migrate
        print("   - Ejecutando migrate...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ Migraciones aplicadas correctamente")
        return True
    except Exception as e:
        print(f"❌ Error ejecutando migraciones: {e}")
        return False

def populate_data():
    """Puebla datos de prueba si no existen"""
    print("\n🌱 Poblando datos de prueba...")
    
    try:
        # Ejecutar comandos de población
        print("   - Poblando países y estados...")
        execute_from_command_line(['manage.py', 'populate_countries_states'])
        
        print("   - Poblando responsabilidades fiscales...")
        execute_from_command_line(['manage.py', 'populate_fiscal_responsibilities'])
        
        print("   - Poblando monedas...")
        execute_from_command_line(['manage.py', 'populate_currencies'])
        
        print("✅ Datos poblados correctamente")
        return True
    except Exception as e:
        print(f"❌ Error poblando datos: {e}")
        return False

def migrate_country_data():
    """Ejecuta la migración de datos del campo país"""
    print("\n🔄 Migrando datos del campo país...")
    
    try:
        # Importar y ejecutar el script de migración
        from misc.fix.migrate_empresa_country_field import migrate_empresa_country_field, verify_migration
        
        migrate_empresa_country_field()
        verify_migration()
        
        print("✅ Migración de datos completada")
        return True
    except Exception as e:
        print(f"❌ Error en migración de datos: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Verificación y corrección de migraciones")
    print("=" * 50)
    
    # Verificar migraciones
    if not verify_migrations():
        print("\n🔄 Aplicando migraciones...")
        if not run_migrations():
            print("❌ No se pudieron aplicar las migraciones")
            return False
    
    # Verificar datos
    if not verify_data():
        print("\n🌱 Poblando datos...")
        if not populate_data():
            print("❌ No se pudieron poblar los datos")
            return False
    
    # Migrar datos del campo país
    print("\n🔄 Verificando migración de datos del campo país...")
    empresas_sin_country = Empresa.objects.filter(country__isnull=True, pais__isnull=False, pais__gt='')
    
    if empresas_sin_country.exists():
        print(f"📊 Encontradas {empresas_sin_country.count()} empresas que requieren migración")
        if not migrate_country_data():
            print("❌ No se pudo completar la migración de datos")
            return False
    else:
        print("✅ No hay empresas que requieran migración de datos")
    
    print("\n🎉 Verificación completada exitosamente!")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 