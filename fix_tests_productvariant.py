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

def fix_productvariant(content):
    # Elimina el argumento name=... de la creación de ProductVariant
    pattern = re.compile(r'ProductVariant\.objects\.create\(([^)]*)name\s*=\s*[^,]+,?\s*([^)]*)\)')
    def repl(match):
        args1 = match.group(1).strip()
        args2 = match.group(2).strip()
        # Combinar argumentos sin name
        if args1 and args2:
            return f"ProductVariant.objects.create({args1}, {args2})"
        elif args1:
            return f"ProductVariant.objects.create({args1})"
        elif args2:
            return f"ProductVariant.objects.create({args2})"
        else:
            return "ProductVariant.objects.create()"
    return re.sub(pattern, repl, content)

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        content = fix_productvariant(content)
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección de name en ProductVariant completada") 