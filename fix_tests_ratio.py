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

def fix_uom_ratio(content):
    # Agregar ratio=1 a las creaciones de UnitOfMeasure que no lo tengan
    pattern = re.compile(r'UnitOfMeasure\.objects\.create\(([^)]*)\)')
    
    def repl(match):
        args = match.group(1)
        if 'ratio=' not in args:
            if args.strip():
                return f"UnitOfMeasure.objects.create({args}, ratio=1)"
            else:
                return "UnitOfMeasure.objects.create(ratio=1)"
        return match.group(0)
    
    return pattern.sub(repl, content)

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        content = fix_uom_ratio(content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección de ratio completada") 