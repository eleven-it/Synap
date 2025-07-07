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

def fix_purchase_request(content):
    # Agregar required_date si no está presente
    pattern = re.compile(r'PurchaseRequest\.objects\.create\(([^)]*)\)')
    def repl(match):
        args = match.group(1)
        if 'required_date=' not in args:
            if args.strip():
                return f"PurchaseRequest.objects.create({args}, required_date=timezone.now().date())"
            else:
                return "PurchaseRequest.objects.create(required_date=timezone.now().date())"
        return match.group(0)
    content = pattern.sub(repl, content)
    
    # Eliminar argumento supplier inválido
    pattern = re.compile(r'PurchaseRequest\.objects\.create\(([^)]*)supplier\s*=\s*[^,]+,?\s*([^)]*)\)')
    def repl2(match):
        args1 = match.group(1).strip()
        args2 = match.group(2).strip()
        if args1 and args2:
            return f"PurchaseRequest.objects.create({args1}, {args2})"
        elif args1:
            return f"PurchaseRequest.objects.create({args1})"
        elif args2:
            return f"PurchaseRequest.objects.create({args2})"
        else:
            return "PurchaseRequest.objects.create()"
    return re.sub(pattern, repl2, content)

def fix_purchase_order(content):
    # Agregar expected_delivery_date si no está presente
    pattern = re.compile(r'PurchaseOrder\.objects\.create\(([^)]*)\)')
    def repl(match):
        args = match.group(1)
        if 'expected_delivery_date=' not in args:
            if args.strip():
                return f"PurchaseOrder.objects.create({args}, expected_delivery_date=timezone.now().date())"
            else:
                return "PurchaseOrder.objects.create(expected_delivery_date=timezone.now().date())"
        return match.group(0)
    return pattern.sub(repl, content)

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        content = fix_purchase_request(content)
        content = fix_purchase_order(content)
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección de campos obligatorios completada") 