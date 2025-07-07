#!/usr/bin/env python3
import os
import re
from decimal import Decimal

files = [
    'purchases/tests/test_models.py',
    'purchases/tests/test_services.py', 
    'purchases/tests/test_views.py',
    'purchases/tests/test_api.py',
    'purchases/tests/test_management_commands.py',
    'purchases/tests/test_integration.py',
    'purchases/tests/test_templates.py'
]

def fix_productvariant_price(content):
    # Agregar price=Decimal('100.00') si no está presente
    pattern = re.compile(r'ProductVariant\.objects\.create\(([^)]*)\)')
    def repl(match):
        args = match.group(1)
        if 'price=' not in args:
            if args.strip():
                return f"ProductVariant.objects.create({args}, price=Decimal('100.00'))"
            else:
                return "ProductVariant.objects.create(price=Decimal('100.00'))"
        return match.group(0)
    return pattern.sub(repl, content)

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        content = fix_productvariant_price(content)
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección de price en ProductVariant completada") 