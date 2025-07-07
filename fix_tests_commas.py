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

def fix_commas(content):
    # Reemplaza comas dobles por una sola coma
    content = re.sub(r',\s*,', ',', content)
    # Limpia comas al inicio o final de los argumentos en ProductVariant.objects.create
    pattern = re.compile(r'ProductVariant\.objects\.create\(([^)]*)\)')
    def repl(match):
        args = match.group(1)
        args = re.sub(r'^\s*,', '', args)
        args = re.sub(r',\s*$', '', args)
        return f"ProductVariant.objects.create({args})"
    content = pattern.sub(repl, content)
    return content

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        content = fix_commas(content)
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección de comas completada") 