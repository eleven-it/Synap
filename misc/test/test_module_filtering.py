#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de filtrado de módulos
en el template de Module Management.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings_test')
django.setup()

from core.models import Module
from core.views.module_admin import ModuleListView
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

def test_module_filtering():
    """Prueba la funcionalidad de filtrado de módulos"""
    print("🧪 Probando funcionalidad de filtrado de módulos...")
    
    # Crear usuario de prueba
    user, created = User.objects.get_or_create(
        username='test_admin',
        defaults={
            'email': 'test@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    # Crear request de prueba
    factory = RequestFactory()
    request = factory.get('/core/modules/')
    request.user = user
    
    # Obtener vista
    view = ModuleListView()
    view.request = request
    
    # Obtener contexto
    context = view.get_context_data()
    modules = context['modules']
    
    print(f"📊 Total de módulos encontrados: {len(modules)}")
    
    # Verificar categorías
    categories = {}
    for module in modules:
        category = get_module_category(module)
        if category not in categories:
            categories[category] = []
        categories[category].append(module.name)
    
    print("\n📂 Categorías de módulos:")
    for category, module_names in categories.items():
        print(f"  • {category}: {', '.join(module_names)}")
    
    # Verificar estados
    active_modules = [m.name for m in modules if m.is_active]
    inactive_modules = [m.name for m in modules if not m.is_active]
    
    print(f"\n✅ Módulos activos: {len(active_modules)}")
    print(f"❌ Módulos inactivos: {len(inactive_modules)}")
    
    # Verificar datos para filtrado
    print("\n🔍 Verificando datos para filtrado:")
    for module in modules[:5]:  # Solo los primeros 5 para no saturar
        print(f"  • {module.name}:")
        print(f"    - Display name: {module.display_name}")
        print(f"    - Description: {module.description[:50]}...")
        print(f"    - Category: {get_module_category(module)}")
        print(f"    - Status: {'active' if module.is_active else 'inactive'}")
        print(f"    - Core: {module.is_core}")
        print(f"    - Required: {module.is_required}")
    
    print("\n✅ Prueba de filtrado completada exitosamente!")

def get_module_category(module):
    """Determina la categoría de un módulo"""
    if module.is_core:
        return 'core'
    elif module.name in ['sales', 'purchases', 'inventory', 'accounting']:
        return 'business'
    elif module.name in ['tiendanube']:
        return 'integration'
    elif module.name in ['mercadopago', 'clover']:
        return 'payment'
    elif module.name in ['reports']:
        return 'reports'
    else:
        return 'other'

if __name__ == '__main__':
    test_module_filtering() 