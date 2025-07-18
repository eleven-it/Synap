#!/usr/bin/env python3
"""
Script para verificar duplicados en archivos de traducción .po
"""

import re
import os

def check_duplicates_in_po(po_file_path):
    """Verificar duplicados en un archivo .po"""
    print(f"🔍 Verificando duplicados en: {po_file_path}")
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar todos los msgid
    msgids = re.findall(r'msgid "([^"]+)"', content)
    
    # Contar ocurrencias
    duplicates = {}
    for msgid in msgids:
        if msgid in duplicates:
            duplicates[msgid] += 1
        else:
            duplicates[msgid] = 1
    
    # Mostrar duplicados
    found_duplicates = False
    for msgid, count in duplicates.items():
        if count > 1:
            print(f"  ❌ Duplicado: '{msgid}' aparece {count} veces")
            found_duplicates = True
    
    if not found_duplicates:
        print(f"  ✅ No se encontraron duplicados")
    
    print(f"  📊 Total de msgid únicos: {len(duplicates)}")
    print(f"  📊 Total de msgid totales: {len(msgids)}")
    
    return found_duplicates

def main():
    """Función principal"""
    print("🔄 Verificando duplicados en archivos de traducción...")
    
    po_files = [
        "locale/es/LC_MESSAGES/django.po",
        "locale/pt/LC_MESSAGES/django.po"
    ]
    
    total_duplicates = 0
    
    for po_file in po_files:
        if os.path.exists(po_file):
            has_duplicates = check_duplicates_in_po(po_file)
            if has_duplicates:
                total_duplicates += 1
            print()
        else:
            print(f"❌ Archivo no encontrado: {po_file}")
    
    if total_duplicates == 0:
        print("✅ No se encontraron duplicados en ningún archivo")
    else:
        print(f"⚠️  Se encontraron duplicados en {total_duplicates} archivo(s)")

if __name__ == "__main__":
    main() 