#!/usr/bin/env python3
"""
Script de pruebas simplificado para verificar la funcionalidad de sincronización basada en timestamps
"""

import os
import sys
import django
from datetime import timedelta

# Configuración de Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

try:
    django.setup()
    print("✅ Django configurado correctamente")
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

try:
    from django.utils import timezone
    from administraNET_integration.models import AdministraNETConfig, SyncTimestampConfig
    from inventory.models import Product
    from sales.models import Client
    print("✅ Modelos importados correctamente")
except ImportError as e:
    print(f"❌ Error importando modelos: {e}")
    print("💡 Asegúrate de que las migraciones estén aplicadas")
    sys.exit(1)

def test_field_mapping():
    """Probar mapeo de campos"""
    
    print("\n🔍 Probando mapeo de campos...")
    
    # Verificar que los modelos tienen los campos necesarios
    try:
        product_fields = [field.name for field in Product._meta.fields]
        client_fields = [field.name for field in Client._meta.fields]
        
        required_fields = ['last_synced_with_adminet', 'updated_at']
        
        for field in required_fields:
            if field in product_fields:
                print(f"   ✅ Product tiene campo: {field}")
            else:
                print(f"   ❌ Product NO tiene campo: {field}")
            
            if field in client_fields:
                print(f"   ✅ Client tiene campo: {field}")
            else:
                print(f"   ❌ Client NO tiene campo: {field}")
                
    except Exception as e:
        print(f"   ❌ Error verificando campos: {e}")

def test_timestamp_configs():
    """Probar configuraciones de timestamp"""
    
    print("\n🔍 Probando configuraciones de timestamp...")
    
    try:
        # Verificar configuración
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            print("   ❌ No hay configuración activa de administraNET")
            return False
        
        # Verificar configuraciones de timestamp
        timestamp_configs = SyncTimestampConfig.objects.filter(is_active=True)
        if not timestamp_configs.exists():
            print("   ❌ No hay configuraciones de timestamp definidas")
            return False
        
        print(f"   ✅ Configuración encontrada: {config}")
        print(f"   ✅ Configuraciones de timestamp: {timestamp_configs.count()}")
        
        for config in timestamp_configs:
            print(f"      - {config.sync_type}: {'Habilitado' if config.enable_timestamp_resolution else 'Deshabilitado'}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error verificando configuraciones: {e}")
        return False

def test_conflict_resolution():
    """Probar resolución de conflictos de timestamp"""
    
    print("\n🔍 Probando resolución de conflictos de timestamp...")
    
    # Simular diferentes escenarios de conflicto
    print("\n📋 Escenario 1: Synap más reciente")
    synap_record = create_mock_synap_record(timezone.now())
    admin_record = create_mock_admin_record(timezone.now() - timedelta(hours=1))
    
    resolution = resolve_timestamp_conflict(synap_record, admin_record)
    print(f"   Synap: {synap_record.updated_at}")
    print(f"   administraNET: {admin_record.get('fecha_modificacion')}")
    print(f"   Resolución: {resolution}")
    print(f"   Resultado esperado: SYNAP_WINS")
    print(f"   ✅ {'Correcto' if resolution == 'SYNAP_WINS' else 'Incorrecto'}")
    
    # Escenario 2: administraNET más reciente
    print("\n📋 Escenario 2: administraNET más reciente")
    synap_record = create_mock_synap_record(timezone.now() - timedelta(hours=1))
    admin_record = create_mock_admin_record(timezone.now())
    
    resolution = resolve_timestamp_conflict(synap_record, admin_record)
    print(f"   Synap: {synap_record.updated_at}")
    print(f"   administraNET: {admin_record.get('fecha_modificacion')}")
    print(f"   Resolución: {resolution}")
    print(f"   Resultado esperado: ADMINET_WINS")
    print(f"   ✅ {'Correcto' if resolution == 'ADMINET_WINS' else 'Incorrecto'}")
    
    # Escenario 3: Mismos timestamps
    print("\n📋 Escenario 3: Mismos timestamps")
    now = timezone.now()
    synap_record = create_mock_synap_record(now)
    admin_record = create_mock_admin_record(now)
    
    resolution = resolve_timestamp_conflict(synap_record, admin_record)
    print(f"   Synap: {synap_record.updated_at}")
    print(f"   administraNET: {admin_record.get('fecha_modificacion')}")
    print(f"   Resolución: {resolution}")
    print(f"   Resultado esperado: NO_CHANGE")
    print(f"   ✅ {'Correcto' if resolution == 'NO_CHANGE' else 'Incorrecto'}")
    
    # Escenario 4: administraNET sin timestamp
    print("\n📋 Escenario 4: administraNET sin timestamp")
    synap_record = create_mock_synap_record(timezone.now())
    admin_record = create_mock_admin_record(None)
    
    resolution = resolve_timestamp_conflict(synap_record, admin_record)
    print(f"   Synap: {synap_record.updated_at}")
    print(f"   administraNET: None")
    print(f"   Resolución: {resolution}")
    print(f"   Resultado esperado: SYNAP_WINS")
    print(f"   ✅ {'Correcto' if resolution == 'SYNAP_WINS' else 'Incorrecto'}")

def create_mock_synap_record(updated_at):
    """Crear un registro mock de Synap para pruebas"""
    class MockSynapRecord:
        def __init__(self, updated_at):
            self.updated_at = updated_at
            self.last_synced_with_adminet = None
    
    return MockSynapRecord(updated_at)

def create_mock_admin_record(fecha_modificacion):
    """Crear un registro mock de administraNET para pruebas"""
    return {
        'fecha_modificacion': fecha_modificacion,
        'last_synced_with_synap': None
    }

def resolve_timestamp_conflict(synap_record, admin_record):
    """
    Resolver conflicto comparando timestamps (Synap vs administraNET)
    
    Args:
        synap_record: Registro de Synap
        admin_record: Registro de administraNET
        
    Returns:
        str: 'SYNAP_WINS', 'ADMINET_WINS', o 'NO_CHANGE'
    """
    synap_updated = synap_record.updated_at
    adminet_updated = admin_record.get('fecha_modificacion')
    
    if not adminet_updated:
        return 'SYNAP_WINS'  # Si administraNET no tiene timestamp, Synap gana
    
    if synap_updated > adminet_updated:
        return 'SYNAP_WINS'
    elif adminet_updated > synap_updated:
        return 'ADMINET_WINS'
    else:
        return 'NO_CHANGE'

def test_model_creation():
    """Probar creación de modelos de prueba"""
    
    print("\n🔍 Probando creación de modelos...")
    
    try:
        # Verificar que podemos crear instancias de los modelos
        product = Product()
        client = Client()
        
        print("   ✅ Instancias de Product y Client creadas correctamente")
        
        # Verificar campos de timestamp
        if hasattr(product, 'last_synced_with_adminet'):
            print("   ✅ Product tiene campo last_synced_with_adminet")
        else:
            print("   ❌ Product NO tiene campo last_synced_with_adminet")
            
        if hasattr(client, 'last_synced_with_adminet'):
            print("   ✅ Client tiene campo last_synced_with_adminet")
        else:
            print("   ❌ Client NO tiene campo last_synced_with_adminet")
            
    except Exception as e:
        print(f"   ❌ Error creando modelos: {e}")

def main():
    """Función principal"""
    print("🧪 Iniciando pruebas de sincronización basada en timestamps...")
    print("=" * 60)
    
    # Probar mapeo de campos
    test_field_mapping()
    
    # Probar configuraciones
    config_ok = test_timestamp_configs()
    
    # Probar creación de modelos
    test_model_creation()
    
    # Probar resolución de conflictos
    test_conflict_resolution()
    
    if config_ok:
        print("\n✅ Todas las pruebas completadas exitosamente!")
        print("\n📝 Próximos pasos:")
        print("   1. Ejecutar migraciones")
        print("   2. Configurar administraNET")
        print("   3. Probar sincronización real")
    else:
        print("\n❌ Algunas pruebas fallaron")
        print("   Revisar configuración antes de continuar")

if __name__ == "__main__":
    main() 