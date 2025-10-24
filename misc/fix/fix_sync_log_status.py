#!/usr/bin/env python
"""
Script para corregir la lógica de estado de los logs de sincronización.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube_administranet.models import SyncLog

def fix_sync_log_status():
    """
    Corregir el estado de los logs de sincronización que muestran éxito cuando fallaron.
    """
    print("🔧 Corrigiendo estado de logs de sincronización...")
    
    # Buscar logs que tienen todos los items fallidos pero están marcados como completados
    problematic_logs = SyncLog.objects.filter(
        status='completed',
        successful_items=0,
        failed_items__gt=0
    )
    
    print(f"📊 Encontrados {problematic_logs.count()} logs problemáticos")
    
    for log in problematic_logs:
        print(f"🔍 Corrigiendo log #{log.id}:")
        print(f"  - Tipo: {log.get_sync_type_display()}")
        print(f"  - Dirección: {log.get_direction_display()}")
        print(f"  - Items exitosos: {log.successful_items}")
        print(f"  - Items fallidos: {log.failed_items}")
        
        # Si todos los items fallaron, marcar como fallido
        if log.failed_items > 0 and log.successful_items == 0:
            log.status = SyncLog.Status.FAILED
            log.error_message = f"Todos los {log.failed_items} items fallaron en la sincronización"
            log.save()
            print(f"  ✅ Corregido: Marcado como FALLIDO")
        else:
            print(f"  ⚠️  No requiere corrección")
        print()
    
    print("✅ Corrección completada")

if __name__ == "__main__":
    fix_sync_log_status()
