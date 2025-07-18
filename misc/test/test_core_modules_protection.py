#!/usr/bin/env python3
"""
Script de prueba para verificar que los módulos core no pueden desactivarse
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings_test')
django.setup()

from core.models import ModuleConfig
from core.views.module_admin import ModuleToggleView, ModuleBulkActionView
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage

User = get_user_model()

def test_core_modules_protection():
    """Prueba que los módulos core no pueden desactivarse"""
    print("🧪 Probando protección de módulos core...")
    
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
    
    # Obtener módulos core
    core_modules = ModuleConfig.objects.filter(is_core=True)
    non_core_modules = ModuleConfig.objects.filter(is_core=False)
    
    print(f"📊 Módulos core encontrados: {core_modules.count()}")
    print(f"📊 Módulos no-core encontrados: {non_core_modules.count()}")
    
    # Probar intento de desactivar módulo core
    if core_modules.exists():
        core_module = core_modules.first()
        print(f"\n🔒 Probando desactivación de módulo core: {core_module.name}")
        
        # Crear request POST para desactivar
        request = factory.post(f'/core/modules/{core_module.name}/toggle/', {
            'action': 'deactivate'
        })
        request.user = user
        
        # Configurar mensajes
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Ejecutar vista
        view = ModuleToggleView()
        response = view.post(request, core_module.name)
        
        # Verificar que el módulo sigue activo
        core_module.refresh_from_db()
        if core_module.is_active:
            print("✅ Módulo core protegido correctamente - sigue activo")
        else:
            print("❌ ERROR: Módulo core fue desactivado")
    
    # Probar desactivación de módulo no-core (debería funcionar)
    if non_core_modules.exists():
        non_core_module = non_core_modules.first()
        print(f"\n🔓 Probando desactivación de módulo no-core: {non_core_module.name}")
        
        # Activar primero si no está activo
        if not non_core_module.is_active:
            non_core_module.is_active = True
            non_core_module.save()
            print(f"  - Activado módulo {non_core_module.name} para la prueba")
        
        # Crear request POST para desactivar
        request = factory.post(f'/core/modules/{non_core_module.name}/toggle/', {
            'action': 'deactivate'
        })
        request.user = user
        
        # Configurar mensajes
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Ejecutar vista
        view = ModuleToggleView()
        response = view.post(request, non_core_module.name)
        
        # Verificar resultado
        non_core_module.refresh_from_db()
        print(f"  - Resultado: {'Desactivado' if not non_core_module.is_active else 'Sigue activo'}")
    
    # Probar acciones masivas con módulos core
    print(f"\n📦 Probando acciones masivas con módulos core...")
    
    if core_modules.exists() and non_core_modules.exists():
        core_module = core_modules.first()
        non_core_module = non_core_modules.first()
        
        # Crear request POST para desactivación masiva
        request = factory.post('/core/modules/bulk-action/', {
            'action': 'deactivate',
            'modules': [core_module.name, non_core_module.name]
        })
        request.user = user
        
        # Configurar mensajes
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Ejecutar vista
        view = ModuleBulkActionView()
        response = view.post(request)
        
        # Verificar resultados
        core_module.refresh_from_db()
        non_core_module.refresh_from_db()
        
        print(f"  - Módulo core {core_module.name}: {'Activo' if core_module.is_active else 'Desactivado'}")
        print(f"  - Módulo no-core {non_core_module.name}: {'Activo' if non_core_module.is_active else 'Desactivado'}")
        
        if core_module.is_active:
            print("✅ Protección de módulos core en acciones masivas funciona correctamente")
        else:
            print("❌ ERROR: Módulo core fue desactivado en acción masiva")
    
    print("\n✅ Prueba de protección de módulos core completada!")

if __name__ == '__main__':
    test_core_modules_protection() 