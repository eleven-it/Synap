#!/usr/bin/env python
"""
Script para actualizar los nombres de las tablas en los mapeos existentes
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from administraNET_integration.models import TableMapping

def update_mapping_tables():
    """Actualizar nombres de tablas en mapeos existentes"""
    
    # Mapeo de nombres de tablas (plural -> singular)
    table_mapping = {
        'articulos': 'articulo',
        'clientes': 'cliente',
        'proveedores': 'proveedor',
        'rubros': 'rubro',
        'marcas': 'marca',
        'subrubros': 'subrubro',
    }
    
    # Actualizar cada mapeo
    mappings = TableMapping.objects.all()
    updated_count = 0
    
    for mapping in mappings:
        old_table = mapping.administraNET_table
        new_table = table_mapping.get(old_table, old_table)
        
        if old_table != new_table:
            print(f"Actualizando {mapping.mapping_type}: {old_table} -> {new_table}")
            mapping.administraNET_table = new_table
            mapping.save()
            updated_count += 1
        else:
            print(f"Mapeo {mapping.mapping_type} ya tiene tabla correcta: {old_table}")
    
    print(f"\nTotal de mapeos actualizados: {updated_count}")

if __name__ == '__main__':
    update_mapping_tables() 