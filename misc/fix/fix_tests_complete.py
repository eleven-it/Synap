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
    # Corregir creación de usuarios
    (r'User\.objects\.create_user\(\s*username=\'[^\']+\',\s*email=\'[^\']+\',\s*password=\'[^\']+\'\)', 
     'User.objects.create_user(email=\'test@example.com\', nombre=\'Test User\', password=\'testpass123\')'),
    
    # Corregir creación de monedas para evitar duplicados
    (r'Currency\.objects\.create\(\s*code="USD",\s*name="US Dollar",\s*symbol="\$"\s*\)',
     'Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$"})[0]'),
    
    # Agregar branch a ApprovalWorkflow
    (r'ApprovalWorkflow\.objects\.create\(\s*empresa=self\.empresa,\s*name="[^"]+"',
     'ApprovalWorkflow.objects.create(empresa=self.empresa, branch=self.branch, name="Flujo Test"'),
    
    # Corregir referencias a sucursal por branch
    (r'sucursal=self\.sucursal', 'branch=self.branch'),
    (r'self\.sucursal', 'self.branch'),
]

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Aplicar reemplazos
        original_content = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Escribir archivo si hubo cambios
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("¡Corrección completada!") 