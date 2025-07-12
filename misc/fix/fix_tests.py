#!/usr/bin/env python3
import os
import re

# Archivos a corregir
files = [
    'purchases/tests/test_models.py',
    'purchases/tests/test_services.py', 
    'purchases/tests/test_views.py',
    'purchases/tests/test_api.py',
    'purchases/tests/test_management_commands.py',
    'purchases/tests/test_integration.py',
    'purchases/tests/test_templates.py'
]

# Reemplazos a hacer
replacements = [
    ('name="Empresa Test"', 'nombre="Empresa Test"'),
    ('tax_id="12345678"', 'identificador_fiscal="12345678"'),
]

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Aplicar reemplazos
        original_content = content
        for old, new in replacements:
            content = content.replace(old, new)
        
        # Escribir archivo si hubo cambios
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("¡Corrección completada!") 