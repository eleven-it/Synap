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

def fix_complex_syntax(content):
    # Corregir líneas con .date() extra al final
    content = re.sub(r'\.date\(\)\)\.date\(\)\s*\+\s*timedelta', '.date() + timedelta', content)
    content = re.sub(r'\.date\(\)\)\.date\(\)$', '.date()', content, flags=re.MULTILINE)
    
    # Corregir líneas que empiezan con coma y tienen required_date mal formateado
    content = re.sub(r',\s*required_date=timezone\.now\(\)\.date\(\), delivery_location=.*?\)\.date\(\)', 
                    ', required_date=timezone.now().date() + timedelta(days=30), delivery_location=self.branch', content)
    
    # Corregir líneas que empiezan con coma y tienen required_date sin timedelta
    content = re.sub(r',\s*required_date=timezone\.now\(\)\.date\(\), delivery_location=.*?\)\.date\(\)$', 
                    ', required_date=timezone.now().date() + timedelta(days=30), delivery_location=self.branch', content, flags=re.MULTILINE)
    
    # Corregir líneas con coma al inicio y expected_delivery_date mal formateado
    content = re.sub(r',\s*expected_delivery_date=timezone\.now\(\)\.date\(\)$', 
                    ', expected_delivery_date=timezone.now().date() + timedelta(days=30)', content, flags=re.MULTILINE)
    
    # Corregir paréntesis desbalanceados al final de líneas
    content = re.sub(r'\)\s*\)\s*$', ')', content, flags=re.MULTILINE)
    
    # Corregir indentación de requested_by
    lines = content.split('\n')
    fixed_lines = []
    for i, line in enumerate(lines):
        if line.strip().startswith('requested_by='):
            # Buscar la línea anterior para obtener la indentación correcta
            if i > 0:
                prev_line = lines[i-1]
                if prev_line.strip().endswith('(') or prev_line.strip().endswith(','):
                    # Usar la misma indentación que la línea anterior
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
        
        content = fix_complex_syntax(content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Corregido")
        else:
            print(f"  - Sin cambios")

print("Corrección compleja de sintaxis completada") 