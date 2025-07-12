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

# Reemplazos para usuarios
user_pattern = re.compile(r"User\.objects\.create_user\(([^)]*)\)")
def fix_user_creation(content):
    def repl(match):
        args = match.group(1)
        # Eliminar username y dejar solo email, nombre y password
        email = re.search(r"email=['\"]([^'\"]+)['\"]", args)
        nombre = re.search(r"nombre=['\"]([^'\"]+)['\"]", args)
        password = re.search(r"password=['\"]([^'\"]+)['\"]", args)
        email_val = email.group(1) if email else 'test@example.com'
        nombre_val = nombre.group(1) if nombre else 'Test User'
        password_val = password.group(1) if password else 'testpass123'
        return f"User.objects.create_user(email='{email_val}', nombre='{nombre_val}', password='{password_val}')"
    return user_pattern.sub(repl, content)

# Reemplazo para branch en ApprovalWorkflow
workflow_pattern = re.compile(r"ApprovalWorkflow\.objects\.create\(([^)]*)\)")
def fix_workflow_branch(content):
    def repl(match):
        args = match.group(1)
        if 'branch=' not in args:
            # Insertar branch=self.branch después de empresa=self.empresa
            args = re.sub(r'(empresa=self\.empresa,)', r'\1 branch=self.branch,', args)
        return f"ApprovalWorkflow.objects.create({args})"
    return workflow_pattern.sub(repl, content)

for file_path in files:
    if os.path.exists(file_path):
        print(f"Procesando {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        content = fix_user_creation(content)
        content = fix_workflow_branch(content)
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("¡Corrección completada!") 