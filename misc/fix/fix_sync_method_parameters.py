#!/usr/bin/env python
"""
Script para corregir los parámetros incorrectos en los métodos de sincronización.
"""

import re

def fix_sync_service_parameters():
    """
    Corregir los parámetros incorrectos en sync_service.py
    """
    file_path = 'tiendanube_administranet/services/sync_service.py'
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Patrones a corregir
    patterns = [
        # sync_products_from_adminet: len(customers) -> len(products)
        (r'def sync_products_from_adminet.*?self\._complete_sync_with_status\(sync_log, successful_syncs, failed_syncs, len\(customers\)\)', 
         lambda m: m.group(0).replace('len(customers)', 'len(products)')),
        
        # sync_products_from_tiendanube: len(customers) -> len(products)  
        (r'def sync_products_from_tiendanube.*?self\._complete_sync_with_status\(sync_log, successful_syncs, failed_syncs, len\(customers\)\)',
         lambda m: m.group(0).replace('len(customers)', 'len(products)')),
         
        # sync_orders_from_adminet: len(customers) -> len(orders)
        (r'def sync_orders_from_adminet.*?self\._complete_sync_with_status\(sync_log, successful_syncs, failed_syncs, len\(customers\)\)',
         lambda m: m.group(0).replace('len(customers)', 'len(orders)')),
         
        # sync_orders_from_tiendanube: len(customers) -> len(orders)
        (r'def sync_orders_from_tiendanube.*?self\._complete_sync_with_status\(sync_log, successful_syncs, failed_syncs, len\(customers\)\)',
         lambda m: m.group(0).replace('len(customers)', 'len(orders)')),
    ]
    
    # Aplicar correcciones
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Escribir archivo corregido
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Parámetros corregidos en sync_service.py")

if __name__ == "__main__":
    fix_sync_service_parameters()
