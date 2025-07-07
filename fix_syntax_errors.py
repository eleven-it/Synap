#!/usr/bin/env python3
import os
import re

files = [
    'purchases/tests/test_models.py',
    'purchases/tests/test_services.py', 
    'purchases/tests/test_views.py',
    'purchases/tests/test_api.py',
    'purchases/tests/test_management_commands.py',
    'purchases/tests/test_integration.py',
    'purchases/tests/test_templates.py'
]

def fix_syntax_errors(content):
    # Corregir timezone.now(, -> timezone.now().date()
    content = re.sub(r'timezone\.now\(\s*,\s*delivery_location', 'timezone.now().date(), delivery_location', content)
    
    # Corregir , required_date=timezone.now(, -> required_date=timezone.now().date()
    content = re.sub(r',\s*required_date=timezone\.now\(\s*,', ', required_date=timezone.now().date(),', content)
    
    # Corregir required_date=timezone.now(, -> required_date=timezone.now().date()
    content = re.sub(r'required_date=timezone\.now\(\s*,', 'required_date=timezone.now().date(),', content)
    
    return content

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        
        content = fix_syntax_errors(content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección de errores de sintaxis completada") 