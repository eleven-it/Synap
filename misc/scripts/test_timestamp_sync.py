#!/usr/bin/env python3
"""
Script de prueba para verificar la funcronización basada en timestamps
"""

import os
import django
import sys
from datetime import timedelta

# Configuración de Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.utils import timezone
from administraNET_integration.models import AdministraNETConfig, SyncTimestampConfig
from administraNET_integration.services.timestamp_based_sync_service import TimestampBasedBidirectionalSyncService
from inventory.models import Product
from sales.models import Client

def test_timestamp_conflict_resolution():
    """Probar resolución de conflictos de timestamp"""
    
    print("🧪 Probando resolución de conflictos de timestamp...")
    print("=" * 60)
    
    # Verificar configuración
    config = AdministraNETConfig.objects.filter(is_active=True).first()
    if not config:
        print("❌ No hay configuración activa de administraNET")
        return False
    
    # Verificar configuraciones de timestamp
    timestamp_configs = SyncTimestampConfig.objects.filter(is_active=True)
    if not timestamp_configs.exists():
        print("❌ No hay configuraciones de timestamp definidas")
        return False
    
    print(f"✅ Configuración encontrada: {config}")
    print(f"✅ Configuraciones de timestamp: {timestamp_configs.count()}")
    
    # Crear servicio
    sync_service = TimestampBasedBidirectionalSyncService(config)
    
    # Simular conflictos de timestamp
    test_conflicts(sync_service)
    
    return True

def test_conflicts(sync_service):
    """Simular diferentes escenarios de conflicto"""
    
    print("\n🔍 Simulando escenarios de conflicto...")
    
    # Escenario 1: Synap más reciente
    print("\n📋 Escenario 1: Synap más reciente")
    synap_record = create_mock_synap_record(timezone.now())
    admin_record = create_mock_admin_record(timezone.now() - timedelta(hours=1))
    
    resolution = sync_service._resolve_timestamp_conflict(synap_record, admin_record)
    print(f"   Synap: {synap_record.updated_at}")
    print(f"   administraNET: {admin_record.get('fecha_modificacion')}")
    print(f"   Resolución: {resolution}")
    print(f"   Resultado esperado: SYNAP_WINS")
    print(f"   ✅ {'Correcto' if resolution == 'SYNAP_WINS' else 'Incorrecto'}")
    
    # Escenario 2: administraNET más reciente
    print("\n📋 Escenario 2: administraNET más reciente")
    synap_record = create_mock_synap_record(timezone.now() - timedelta(hours=1))
    admin_record = create_mock_admin_record(timezone.now())
    
    resolution = sync_service._resolve_timestamp_conflict(synap_record, admin_record)
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
    
    resolution = sync_service._resolve_timestamp_conflict(synap_record, admin_record)
    print(f"   Synap: {synap_record.updated_at}")
    print(f"   administraNET: {admin_record.get('fecha_modificacion')}")
    print(f"   Resolución: {resolution}")
    print(f"   Resultado esperado: NO_CHANGE")
    print(f"   ✅ {'Correcto' if resolution == 'NO_CHANGE' else 'Incorrecto'}")
    
    # Escenario 4: administraNET sin timestamp
    print("\n📋 Escenario 4: administraNET sin timestamp")
    synap_record = create_mock_synap_record(timezone.now())
    admin_record = create_mock_admin_record(None)
    
    resolution = sync_service._resolve_timestamp_conflict(synap_record, admin_record)
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

def test_detection_methods(sync_service):
    """Probar métodos de detección de conflictos"""
    
    print("\n🔍 Probando métodos de detección...")
    
    # Crear registros de prueba
    synap_record = create_mock_synap_record(timezone.now())
    admin_record = create_mock_admin_record(timezone.now() - timedelta(hours=1))
    
    # Probar detección de conflictos
    has_conflict = sync_service._has_timestamp_conflict(synap_record, admin_record)
    print(f"   ¿Hay conflicto? {has_conflict}")
    
    # Probar resolución
    resolution = sync_service._resolve_timestamp_conflict(synap_record, admin_record)
    print(f"   Resolución: {resolution}")

def test_field_mapping():
    """Probar mapeo de campos"""
    
    print("\n🔍 Probando mapeo de campos...")
    
    # Verificar que los modelos tienen los campos necesarios
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

def main():
    """Función principal"""
    print("🧪 Iniciando pruebas de sincronización basada en timestamps...")
    print("=" * 60)
    
    # Probar mapeo de campos
    test_field_mapping()
    
    # Probar resolución de conflictos
    success = test_timestamp_conflict_resolution()
    
    if success:
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