#!/usr/bin/env python
"""
Script para migrar datos existentes al sistema unificado de sincronización de clientes.
Migra datos de TiendaNubeCustomerMapping y TiendaNubeClienteMap a TiendaNubeUnifiedCustomerMapping.
"""

import os
import sys
import django
from django.db import transaction
from django.utils import timezone

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube.models_synap import TiendaNubeCustomerMapping
from tiendanube.models_adminet import TiendaNubeClienteMap
from tiendanube.models_unified import TiendaNubeUnifiedCustomerMapping, TiendaNubeUnifiedConfig
from tiendanube.models_synap import TiendaNubeConfig
from tiendanube.models_adminet import TiendaNubeAdminetConfig

def migrate_customer_mappings():
    """Migra los mapeos de clientes existentes al sistema unificado."""
    print("🔄 Migrando mapeos de clientes existentes...")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    try:
        with transaction.atomic():
            # Migrar TiendaNubeCustomerMapping (Synap ↔ Tiendanube)
            print("📊 Migrando TiendaNubeCustomerMapping...")
            for mapping in TiendaNubeCustomerMapping.objects.all():
                try:
                    # Verificar si ya existe un mapeo unificado para este email
                    if TiendaNubeUnifiedCustomerMapping.objects.filter(
                        tiendanube_email=mapping.tiendanube_email
                    ).exists():
                        print(f"⚠️  Saltando {mapping.tiendanube_email} - ya existe en sistema unificado")
                        skipped_count += 1
                        continue
                    
                    # Crear mapeo unificado
                    unified_mapping = TiendaNubeUnifiedCustomerMapping.objects.create(
                        tiendanube_id=mapping.tiendanube_id,
                        tiendanube_email=mapping.tiendanube_email,
                        tiendanube_document=mapping.tiendanube_document,
                        synap_client=mapping.client,
                        sync_direction='bidirectional',
                        sync_status=mapping.sync_status,
                        sync_enabled=mapping.sync_enabled,
                        error_message=mapping.error_message,
                        last_synced=mapping.last_synced
                    )
                    
                    print(f"✅ Migrado: {mapping.tiendanube_email} (Synap ↔ Tiendanube)")
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"❌ Error migrando {mapping.tiendanube_email}: {str(e)}")
                    error_count += 1
            
            # Migrar TiendaNubeClienteMap (Tiendanube ↔ AdministraNET)
            print("📊 Migrando TiendaNubeClienteMap...")
            for mapping in TiendaNubeClienteMap.objects.all():
                try:
                    # Verificar si ya existe un mapeo unificado para este email
                    existing_unified = TiendaNubeUnifiedCustomerMapping.objects.filter(
                        tiendanube_email=mapping.tiendanube_email
                    ).first()
                    
                    if existing_unified:
                        # Actualizar mapeo existente con datos de AdministraNET
                        existing_unified.adminet_codigo = mapping.adminet_codigo
                        existing_unified.adminet_nombre = mapping.adminet_nombre
                        existing_unified.adminet_documento = mapping.adminet_documento
                        existing_unified.sync_direction = 'bidirectional'
                        existing_unified.save()
                        
                        print(f"🔄 Actualizado: {mapping.tiendanube_email} (agregado AdministraNET)")
                        migrated_count += 1
                    else:
                        # Crear nuevo mapeo unificado solo con AdministraNET
                        unified_mapping = TiendaNubeUnifiedCustomerMapping.objects.create(
                            tiendanube_email=mapping.tiendanube_email,
                            adminet_codigo=mapping.adminet_codigo,
                            adminet_nombre=mapping.adminet_nombre,
                            adminet_documento=mapping.adminet_documento,
                            sync_direction='adminet_only',
                            sync_status='synced' if mapping.activo else 'pending',
                            sync_enabled=mapping.activo
                        )
                        
                        print(f"✅ Migrado: {mapping.tiendanube_email} (AdministraNET only)")
                        migrated_count += 1
                        
                except Exception as e:
                    print(f"❌ Error migrando {mapping.tiendanube_email}: {str(e)}")
                    error_count += 1
    
    except Exception as e:
        print(f"❌ Error general en migración: {str(e)}")
        return False
    
    print(f"\n📈 Resumen de migración:")
    print(f"   ✅ Migrados: {migrated_count}")
    print(f"   ⚠️  Saltados: {skipped_count}")
    print(f"   ❌ Errores: {error_count}")
    
    return True

def create_unified_config():
    """Crea una configuración unificada basada en las configuraciones existentes."""
    print("⚙️  Creando configuración unificada...")
    
    try:
        # Verificar si ya existe una configuración unificada
        if TiendaNubeUnifiedConfig.objects.filter(is_active=True).exists():
            print("⚠️  Ya existe una configuración unificada activa")
            return True
        
        # Obtener configuración de Tiendanube
        tiendanube_config = TiendaNubeConfig.objects.filter(is_active=True).first()
        
        # Obtener configuración de AdministraNET
        adminet_config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config and not adminet_config:
            print("⚠️  No hay configuraciones existentes para migrar")
            return True
        
        # Crear configuración unificada
        unified_config = TiendaNubeUnifiedConfig.objects.create(
            name="Configuración Migrada",
            is_active=True,
            sync_mode='manual',
            # Configuración de Tiendanube
            tiendanube_store_id=tiendanube_config.store_id if tiendanube_config else '',
            tiendanube_access_token=tiendanube_config.access_token if tiendanube_config else '',
            tiendanube_api_url=getattr(tiendanube_config, 'api_url', 'https://api.tiendanube.com/v1') if tiendanube_config else 'https://api.tiendanube.com/v1',
            # Configuración de AdministraNET
            adminet_host=adminet_config.host if adminet_config else '',
            adminet_port=adminet_config.port if adminet_config else 3306,
            adminet_database=adminet_config.database if adminet_config else '',
            adminet_user=adminet_config.user if adminet_config else '',
            adminet_password=adminet_config.password if adminet_config else '',
            # Configuración de sincronización
            sync_interval=getattr(tiendanube_config, 'sync_interval', 30) if tiendanube_config else 30,
            batch_size=100,
            max_retries=3,
            notify_on_error=True
        )
        
        print(f"✅ Configuración unificada creada: {unified_config.name}")
        return True
        
    except Exception as e:
        print(f"❌ Error creando configuración unificada: {str(e)}")
        return False

def verify_migration():
    """Verifica que la migración se haya completado correctamente."""
    print("🔍 Verificando migración...")
    
    try:
        # Contar registros originales
        original_synap_count = TiendaNubeCustomerMapping.objects.count()
        original_adminet_count = TiendaNubeClienteMap.objects.count()
        
        # Contar registros unificados
        unified_count = TiendaNubeUnifiedCustomerMapping.objects.count()
        
        # Contar configuraciones
        unified_config_count = TiendaNubeUnifiedConfig.objects.filter(is_active=True).count()
        
        print(f"📊 Estadísticas de migración:")
        print(f"   📋 TiendaNubeCustomerMapping originales: {original_synap_count}")
        print(f"   📋 TiendaNubeClienteMap originales: {original_adminet_count}")
        print(f"   🔗 TiendaNubeUnifiedCustomerMapping: {unified_count}")
        print(f"   ⚙️  Configuraciones unificadas activas: {unified_config_count}")
        
        # Verificar que todos los emails únicos estén migrados
        synap_emails = set(TiendaNubeCustomerMapping.objects.values_list('tiendanube_email', flat=True))
        adminet_emails = set(TiendaNubeClienteMap.objects.values_list('tiendanube_email', flat=True))
        unified_emails = set(TiendaNubeUnifiedCustomerMapping.objects.values_list('tiendanube_email', flat=True))
        
        all_original_emails = synap_emails.union(adminet_emails)
        missing_emails = all_original_emails - unified_emails
        
        if missing_emails:
            print(f"⚠️  Emails faltantes en migración: {len(missing_emails)}")
            for email in list(missing_emails)[:5]:  # Mostrar solo los primeros 5
                print(f"      - {email}")
        else:
            print("✅ Todos los emails han sido migrados correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando migración: {str(e)}")
        return False

def main():
    """Función principal del script."""
    print("🚀 Iniciando migración al sistema unificado de sincronización de clientes")
    print("=" * 70)
    
    # Crear configuración unificada
    if not create_unified_config():
        print("❌ Error creando configuración unificada")
        return False
    
    # Migrar mapeos de clientes
    if not migrate_customer_mappings():
        print("❌ Error migrando mapeos de clientes")
        return False
    
    # Verificar migración
    if not verify_migration():
        print("❌ Error verificando migración")
        return False
    
    print("\n🎉 Migración completada exitosamente!")
    print("=" * 70)
    print("📝 Próximos pasos:")
    print("   1. Verificar que el dashboard unificado funcione correctamente")
    print("   2. Probar las funcionalidades de sincronización")
    print("   3. Considerar eliminar los modelos antiguos después de validar")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 