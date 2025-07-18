#!/usr/bin/env python3
"""
Script para corregir referencias de empresa.nombre por empresa.name en templates de accounting
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
        
        # Buscar y reemplazar emp.nombre por emp.name
        content = re.sub(r'emp\.nombre', 'emp.name', content)
        
        # Si hubo cambios, escribir el archivo
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Corregido: {file_path}")
            return True
        else:
            print(f"⏭️  Sin cambios: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error en {file_path}: {e}")
        return False

def main():
    """Función principal"""
    accounting_templates_dir = "accounting/templates/accounting"
    
    if not os.path.exists(accounting_templates_dir):
        print(f"❌ Directorio no encontrado: {accounting_templates_dir}")
        return
    
    print("🔧 Corrigiendo templates de accounting...")
    
    total_files = 0
    corrected_files = 0
    
    # Recorrer todos los archivos HTML en el directorio y subdirectorios
    for root, dirs, files in os.walk(accounting_templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                total_files += 1
                if fix_template_file(file_path):
                    corrected_files += 1
    
    print(f"\n📊 Resumen:")
    print(f"   Total de archivos procesados: {total_files}")
    print(f"   Archivos corregidos: {corrected_files}")
    print(f"   Archivos sin cambios: {total_files - corrected_files}")
    
    if corrected_files > 0:
        print(f"\n✅ Corrección completada exitosamente!")
    else:
        print(f"\nℹ️  No se encontraron referencias a corregir.")

if __name__ == "__main__":
    main() 