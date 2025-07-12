#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import os

def update_translations():
    """Actualiza masivamente todas las traducciones en el archivo django.po"""
    
    po_file = "locale/es/LC_MESSAGES/django.po"
    
    # Verificar que el archivo existe
    if not os.path.exists(po_file):
        print(f"❌ Error: No se encontró el archivo {po_file}")
        return
    
    print("🔄 Leyendo archivo de traducciones...")
    
    # Leer el archivo
    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Diccionario de traducciones: inglés -> español
    translations = {
        # Templates base y navegación
        "Welcome to Synap. Select an app to start working.": "Bienvenido a Synap. Selecciona una aplicación para comenzar a trabajar.",
        "Hello, %(name)s! 👋": "¡Hola, %(name)s! 👋",
        "Active Company": "Empresa Activa",
        "Assigned Roles": "Roles Asignados",
        "Available Apps": "Aplicaciones Disponibles",
        "Available Applications": "Aplicaciones Disponibles",
        "Access Information": "Información de Acceso",
        "Detailed Permissions": "Permisos Detallados",
        "Quick Actions": "Acciones Rápidas",
        "See Menu Example": "Ver Ejemplo de Menú",
        "Classic Dashboard": "Dashboard Clásico",
        "Inventory": "Inventario",
        "Manage stock": "Gestionar stock",
        "New architecture": "Nueva arquitectura",
        "Classic view": "Vista clásica",
        "You have no assigned roles": "No tienes roles asignados",
        "You have no assigned permissions": "No tienes permisos asignados",
        "Language": "Idioma",
        "Not specified": "No especificado",
        "Total: %(total)s permissions": "Total: %(total)s permisos",
        "Dark": "Oscuro",
        "Manage": "Gestionar",
        "and related settings": "y configuraciones relacionadas",
        "Go to": "Ir al",
        "Dashboard": "Dashboard",
        
        # Formularios y acciones
        "Create Product": "Crear Producto",
        "Save Product": "Guardar Producto",
        "Cancel": "Cancelar",
        "Edit": "Editar",
        "Delete": "Eliminar",
        "Active": "Activo",
        "Inactive": "Inactivo",
        "Create Unit": "Crear Unidad",
        "Create Currency": "Crear Moneda",
        "No units of measure registered.": "No hay unidades de medida registradas.",
        "No currencies registered.": "No hay monedas registradas.",
        "No products registered.": "No hay productos registrados.",
        "No stock registered.": "No hay stock registrado.",
        
        # Campos de formulario
        "Product Name": "Nombre del Producto",
        "SKU": "SKU",
        "Name": "Nombre",
        "Description": "Descripción",
        "Brand": "Marca",
        "Category": "Categoría",
        "Subcategory": "Subcategoría",
        "Price": "Precio",
        "Currency": "Moneda",
        "Unit": "Unidad",
        "Image": "Imagen",
        "Actions": "Acciones",
        "Status": "Estado",
        "Code": "Código",
        "Symbol": "Símbolo",
        "Order": "Orden",
        "ID": "ID",
        "Identification": "Identificación",
        "Organization": "Organización",
        "Prices and Margins": "Precios y Márgenes",
        "Weight and Dimensions": "Peso y Dimensiones",
        "Multimedia": "Multimedia",
        "Others": "Otros",
        "Product Images": "Imágenes del Producto",
        "Upload images": "Subir imágenes",
        "Product image": "Imagen del producto",
        "Zoom image": "Zoom de imagen",
        
        # Placeholders y textos de ayuda
        "Product name": "Nombre del producto",
        "Unique SKU": "SKU único",
        "example-product": "ejemplo-producto",
        "Friendly URL automatically suggested from the name, you can modify it if you wish.": "URL amigable sugerida automáticamente a partir del nombre, puedes modificarla si lo deseas.",
        "Barcode": "Código de Barras",
        "Optional": "Opcional",
        "Describe the product": "Describe el producto",
        "Type or select a category...": "Escribe o selecciona una categoría...",
        "Type or select a subcategory...": "Escribe o selecciona una subcategoría...",
        "Type or select a brand...": "Escribe o selecciona una marca...",
        "Sale price": "Precio de venta",
        "Promotional Price": "Precio Promocional",
        "Offer price": "Precio en oferta",
        "Cost Price": "Precio de Costo",
        "Cost": "Costo",
        "Profit Margin (%)": "Margen de Ganancia (%)",
        "Margin %": "Margen %",
        "Weight (kg)": "Peso (kg)",
        "Volume (m³)": "Volumen (m³)",
        "Width (cm)": "Ancho (cm)",
        "Height (cm)": "Alto (cm)",
        "Depth (cm)": "Profundidad (cm)",
        "Is Dangerous Goods": "Es Mercancía Peligrosa",
        "Video (YouTube/Vimeo)": "Video (YouTube/Vimeo)",
        "Video link": "Enlace de video",
        "Paste a YouTube or Vimeo link to show a video in the product gallery.": "Pega un enlace de YouTube o Vimeo para mostrar un video en la galería del producto.",
        "Unit of Measure": "Unidad de Medida",
        "Tracking Type": "Tipo de Seguimiento",
        "Published": "Publicado",
        "PNG, JPG, GIF up to 10MB each. Max 250 images.": "PNG, JPG, GIF hasta 10MB cada una. Máx 250 imágenes.",
        "Drag and drop or click to select files": "Arrastra y suelta o haz click para seleccionar archivos",
        "Format not allowed. Only PNG, JPG, GIF.": "Formato no permitido. Solo PNG, JPG, GIF.",
        "File exceeds maximum size of 10MB.": "El archivo supera el tamaño máximo de 10MB.",
        "Loading...": "Cargando...",
        "most used": "más usada",
        "Other brands": "Otras marcas",
        "Create": "Crear",
        "Error creating brand": "Error al crear la marca",
        "Other categories": "Otras categorías",
        "Error creating category": "Error al crear la categoría",
        "Select a category first...": "Selecciona un rubro primero...",
        "Other subcategories": "Otras subcategorías",
        "Select a category before creating a subcategory": "Selecciona un rubro antes de crear una subcategoría",
        "Error creating subcategory": "Error al crear la subcategoría",
        
        # Ejemplos y valores
        "Ex: 1.5": "Ej: 1.5",
        "Ex: 0.01": "Ej: 0.01",
        "Ex: 10": "Ej: 10",
        "Ex: 20": "Ej: 20",
        "Ex: 5": "Ej: 5",
        
        # Dashboard específico
        "Inventory Dashboard": "Dashboard de Inventario",
        "Welcome to the inventory dashboard. Here you can see the current stock status by product and location.": "Bienvenido al dashboard de inventario. Aquí puedes ver el estado actual del stock por producto y ubicación.",
        "Total Products": "Total de Productos",
        "Total Locations": "Total de Ubicaciones",
        "Total Stock Movements": "Total de Movimientos de Stock",
        "Stock by Product & Location": "Stock por Producto y Ubicación",
        "Available Stock": "Stock Disponible",
        "Reserved": "Reservado",
        "Total": "Total",
        "You do not have permission to view the inventory dashboard.": "No tienes permisos para ver el dashboard de inventario.",
        
        # Apps específicas
        "Customers": "Clientes",
        "Suppliers": "Proveedores",
        "This is your panel as a": "Este es tu panel como",
        "customer": "cliente",
        "supplier": "proveedor",
        "This action cannot be undone.": "Esta acción no se puede deshacer.",
        
        # Permisos y acceso
        "You do not have sufficient permissions to access this section.": "No tienes permisos suficientes para acceder a esta sección.",
        "Back to home": "Volver al inicio",
        
        # Configuración del sistema
        "Configuration": "Configuración",
        "System Configuration": "Configuración del Sistema",
        "System Configurations": "Configuraciones del Sistema",
        "Units of Measure": "Unidades de Medida",
        "Currencies": "Monedas",
        "Exchange Rate": "Tipo de Cambio",
        "Exchange Rates": "Tipos de Cambio",
        
        # Modelos y campos
        "Company": "Empresa",
        "Branch": "Sucursal",
        "Branches": "Sucursales",
        "Branch Name": "Nombre de Sucursal",
        "Internal Code": "Código Interno",
        "State/Province": "Estado/Provincia",
        "Country": "País",
        "Phone": "Teléfono",
        "Created at": "Creado en",
        "Updated at": "Actualizado en",
        
        # Idiomas
        "Spanish": "Español",
        "English": "Inglés",
        "Portuguese": "Portugués",
        
        # Roles y permisos
        "Role": "Rol",
        "Roles": "Roles",
        "Permission": "Permiso",
        "Extended User": "Usuario Extendido",
        "Extended Users": "Usuarios Extendidos",
        
        # Mensajes de error y validación
        "No submenus": "Sin submenús",
        "more": "más",
        "more sections": "más secciones"
    }
    
    print(f"📝 Actualizando {len(translations)} traducciones...")
    
    # Contador de actualizaciones
    updated_count = 0
    
    # Actualizar cada traducción
    for english, spanish in translations.items():
        # Escapar caracteres especiales para regex
        escaped_english = re.escape(english)
        
        # Patrón para encontrar msgid vacío
        pattern_empty = rf'msgid "{escaped_english}"\nmsgstr ""'
        replacement_empty = f'msgid "{english}"\nmsgstr "{spanish}"'
        
        # Patrón para encontrar msgid con traducción existente
        pattern_existing = rf'msgid "{escaped_english}"\nmsgstr "[^"]*"'
        replacement_existing = f'msgid "{english}"\nmsgstr "{spanish}"'
        
        # Aplicar reemplazos
        original_content = content
        content = re.sub(pattern_empty, replacement_empty, content)
        content = re.sub(pattern_existing, replacement_existing, content)
        
        # Verificar si se hizo algún cambio
        if content != original_content:
            updated_count += 1
    
    # Guardar el archivo actualizado
    with open(po_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Se actualizaron {updated_count} traducciones")
    print("🔄 Compilando traducciones...")
    
    # Compilar las traducciones
    os.system("docker exec Synap_app python manage.py compilemessages")
    
    print("�� ¡Proceso completado! Las traducciones han sido actualizadas y compiladas.")

if __name__ == "__main__":
    update_translations()
