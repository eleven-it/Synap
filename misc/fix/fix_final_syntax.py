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
    # Corregir paréntesis desbalanceados en timezone.now().date()
    content = re.sub(r'\.date\(\)\)$', '.date()', content, flags=re.MULTILINE)
    content = re.sub(r'\.date\(\)\)\s*\)$', '.date())', content, flags=re.MULTILINE)
    
    # Corregir líneas que terminan con .date()).date())
    content = re.sub(r'\.date\(\)\)\.date\(\)\)$', '.date())', content, flags=re.MULTILINE)
    
    # Corregir indentación de líneas que empiezan con requested_by
    lines = content.split('\n')
    fixed_lines = []
    for line in lines:
        if line.strip().startswith('requested_by='):
            # Buscar la línea anterior para obtener la indentación correcta
            if fixed_lines:
                prev_line = fixed_lines[-1]
                if prev_line.strip().endswith('('):
                    # Si la línea anterior termina con (, usar la misma indentación
                    indent = len(prev_line) - len(prev_line.lstrip())
                    line = ' ' * indent + line.strip()
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

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

print("Corrección final de sintaxis completada") 