#!/usr/bin/env python3
"""
Script para agregar traducciones de empresa a los archivos .po
"""

import os
import re

# Traducciones de empresa en inglés -> español
COMPANY_TRANSLATIONS = {
    # Títulos y navegación
    "Companies": "Empresas",
    "New Company": "Nueva Empresa",
    "Create First Company": "Crear Primera Empresa",
    "Back to Companies": "Volver a Empresas",
    
    # Estados
    "Active": "Activa",
    "Inactive": "Inactiva",
    "company": "empresa",
    
    # Acciones
    "Edit company": "Editar empresa",
    "Edit": "Editar",
    "View branches": "Ver sucursales",
    "Branches": "Sucursales",
    "View company details": "Ver ficha de la empresa",
    "Details": "Ficha",
    "Activate/deactivate company": "Activar/desactivar empresa",
    
    # Mensajes de estado
    "No companies registered": "No hay empresas registradas",
    "Start by creating your first company to manage your business efficiently.": "Comienza creando tu primera empresa para gestionar tu negocio de manera eficiente.",
    "Company activated": "Empresa activada",
    "Company deactivated": "Empresa desactivada",
    "Error updating status": "Error al actualizar el estado",
    
    # Confirmación de eliminación
    "Are you sure you want to delete the company": "¿Estás seguro de que deseas eliminar la empresa",
    "This action cannot be undone.": "Esta acción no se puede deshacer.",
    
    # Formulario de empresa
    "Company Name": "Nombre de la empresa",
    "Business Name": "Razón social",
    "Country": "País",
    "State/Province": "Provincia/Estado",
    "City": "Ciudad",
    "Address": "Dirección",
    "Phone": "Teléfono",
    "Email": "Email",
    "Website": "Sitio web",
    "Tax ID": "CUIT/RFC/NIF",
    "Tax Responsibility Type": "Tipo de responsabilidad",
    "Currency": "Moneda",
    "Cancel": "Cancelar",
    "Save Changes": "Guardar cambios",
    "Create Company": "Crear empresa",
    "Click or drag an image": "Haz click o arrastra una imagen",
    "Only image files are allowed (JPG, PNG, SVG, etc).": "Solo se permiten archivos de imagen (JPG, PNG, SVG, etc).",
    "Searching...": "Buscando...",
    "No results": "Sin resultados",
    
    # Confirmación de eliminación
    "Confirm Deletion": "Confirmar Eliminación",
    "Delete company?": "¿Eliminar empresa?",
    "What will be deleted?": "¿Qué se eliminará?",
    "All company data": "Todos los datos de la empresa",
    "Associated configurations": "Configuraciones asociadas",
    "Logo and related files": "Logo y archivos relacionados",
    "This action is permanent": "Esta acción es permanente",
    "Yes, delete company": "Sí, eliminar empresa",
}

def add_translations_to_po(po_file_path, translations):
    """Agregar traducciones a un archivo .po"""
    
    # Leer el archivo actual
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar las traducciones existentes
    existing_msgids = re.findall(r'msgid "([^"]+)"', content)
    
    # Preparar nuevas traducciones
    new_translations = []
    added_count = 0
    
    for english, spanish in translations.items():
        if english not in existing_msgids:
            new_translations.append(f'''
#: core/templates/core/system_config/empresa_list.html
#: core/templates/core/system_config/empresa_detail.html
#: core/templates/core/system_config/empresa_confirm_delete.html
msgid "{english}"
msgstr "{spanish}"
''')
            added_count += 1
    
    if new_translations:
        # Insertar antes del último msgid (antes de las traducciones del sistema)
        # Buscar el último msgid para insertar antes
        last_msgid_pos = content.rfind('\nmsgid "')
        if last_msgid_pos != -1:
            # Insertar antes del último msgid
            content = content[:last_msgid_pos] + ''.join(new_translations) + content[last_msgid_pos:]
        else:
            # Si no hay msgid, agregar al final
            content += ''.join(new_translations)
        
        # Escribir el archivo actualizado
        with open(po_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Agregadas {added_count} traducciones a {po_file_path}")
    else:
        print(f"ℹ️  No se agregaron nuevas traducciones a {po_file_path}")

def main():
    """Función principal"""
    print("🔄 Agregando traducciones de empresa...")
    
    # Archivos .po a actualizar
    po_files = [
        "locale/es/LC_MESSAGES/django.po",
        "locale/pt/LC_MESSAGES/django.po"
    ]
    
    for po_file in po_files:
        if os.path.exists(po_file):
            add_translations_to_po(po_file, COMPANY_TRANSLATIONS)
        else:
            print(f"❌ Archivo no encontrado: {po_file}")
    
    print("✅ Proceso completado")

if __name__ == "__main__":
    main() 