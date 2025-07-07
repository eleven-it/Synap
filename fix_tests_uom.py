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

pattern = re.compile(r'UnitOfMeasure\.objects\.create\(([^)]*)empresa\s*=\s*[^,]+,?([^)]*)\)')

def fix_uom(content):
    # Elimina el argumento empresa=... de la creación de UnitOfMeasure
    return re.sub(pattern, lambda m: f"UnitOfMeasure.objects.create({m.group(1)}{m.group(2)})", content)

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        content = fix_uom(content)
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("¡Corrección completada!") 