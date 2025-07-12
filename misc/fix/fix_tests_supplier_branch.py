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

def fix_product_args(content):
    # Corrige price=Decimal('100.00', branch=self.branch) -> price=Decimal('100.00'), branch=self.branch
    pattern = re.compile(r"price=Decimal\('100.00', branch=self.branch\)")
    content = pattern.sub("price=Decimal('100.00'), branch=self.branch", content)
    # Si hay Product.objects.create(..., price=Decimal('100.00'), branch=self.branch, ...branch=self.branch...) duplicado, dejar solo uno
    content = re.sub(r',\s*branch=self.branch,\s*branch=self.branch', ', branch=self.branch', content)
    return content

def fix_supplier_branch(content):
    # Agregar branch=self.branch si no está presente
    pattern = re.compile(r'Supplier\.objects\.create\(([^)]*)\)')
    def repl(match):
        args = match.group(1)
        if 'branch=' not in args:
            if args.strip():
                return f"Supplier.objects.create({args}, branch=self.branch)"
            else:
                return "Supplier.objects.create(branch=self.branch)"
        return match.group(0)
    return pattern.sub(repl, content)

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        content = fix_product_args(content)
        content = fix_supplier_branch(content)
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección de branch en Product y Supplier completada") 