#!/usr/bin/env python3
"""
Script para corregir referencias de empresa.nombre por empresa.name en templates de reports
"""

import os
import re

def fix_template_file(file_path):
    """Corregir referencias en un archivo de template"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar y reemplazar empresa.nombre por empresa.name
        original_content = content
        content = re.sub(r'empresa\.nombre', 'empresa.name', content)
        
        # Si hubo cambios, escribir el archivo
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corregido: {file_path}")
            return True
        else:
            print(f"ℹ️  Sin cambios: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error en {file_path}: {e}")
        return False

def main():
    """Función principal"""
    reports_templates_dir = "reports/templates/reports"
    
    if not os.path.exists(reports_templates_dir):
        print(f"❌ Directorio no encontrado: {reports_templates_dir}")
        return
    
    # Lista de archivos que necesitan corrección
    files_to_fix = [
        "dashboard.html",
        "schedule_form.html", 
        "report_builder.html",
        "report_detail.html",
        "report_list.html",
        "report_preview.html",
        "template_list.html",
        "component_library.html",
        "schedule_detail.html",
        "template_detail.html",
        "schedule_list.html"
    ]
    
    fixed_count = 0
    total_count = len(files_to_fix)
    
    print("🔧 Corrigiendo templates de reports...")
    print("=" * 50)
    
    for filename in files_to_fix:
        file_path = os.path.join(reports_templates_dir, filename)
        if os.path.exists(file_path):
            if fix_template_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  Archivo no encontrado: {file_path}")
    
    print("=" * 50)
    print(f"📊 Resumen: {fixed_count}/{total_count} archivos corregidos")

if __name__ == "__main__":
    main() 