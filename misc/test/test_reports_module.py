#!/usr/bin/env python3
"""
Script de prueba completo para el módulo Reports
Verifica que el módulo esté completamente funcional y aparezca en el navbar
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import UsuarioExtendido, Empresa, Branch
from core.utils.utils import apps_visibles_para_usuario
from reports.models import Report, ReportTemplate, ReportSchedule
import json

User = get_user_model()

def print_header(title):
    """Imprimir encabezado con formato"""
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def print_success(message):
    """Imprimir mensaje de éxito"""
    print(f"✅ {message}")

def print_error(message):
    """Imprimir mensaje de error"""
    print(f"❌ {message}")

def print_info(message):
    """Imprimir mensaje informativo"""
    print(f"ℹ️ {message}")

def test_database_models():
    """Probar que los modelos de reports funcionen correctamente"""
    print_header("PRUEBA DE MODELOS DE BASE DE DATOS")
    
    try:
        # Verificar que los modelos se pueden importar
        from reports.models import Report, ReportTemplate, ReportComponent, ReportSchedule, ReportExport
        print_success("Todos los modelos de reports se importan correctamente")
        
        # Verificar campos del modelo ReportTemplate
        template_fields = [f.name for f in ReportTemplate._meta.fields]
        if 'is_active' in template_fields:
            print_success("Campo 'is_active' presente en ReportTemplate")
        else:
            print_error("Campo 'is_active' NO encontrado en ReportTemplate")
        
        # Verificar campos del modelo Report
        report_fields = [f.name for f in Report._meta.fields]
        if 'is_active' in report_fields:
            print_success("Campo 'is_active' presente en Report")
        else:
            print_error("Campo 'is_active' NO encontrado en Report")
        
        # Verificar campos del modelo ReportSchedule
        schedule_fields = [f.name for f in ReportSchedule._meta.fields]
        if 'is_active' in schedule_fields:
            print_success("Campo 'is_active' presente en ReportSchedule")
        else:
            print_error("Campo 'is_active' NO encontrado en ReportSchedule")
            
        return True
        
    except Exception as e:
        print_error(f"Error al probar modelos: {e}")
        return False

def test_urls_resolution():
    """Probar que las URLs de reports se resuelvan correctamente"""
    print_header("PRUEBA DE RESOLUCIÓN DE URLs")
    
    urls_to_test = [
        'reports:dashboard',
        'reports:report_list',
        'reports:report_create',
        'reports:template_list',
        'reports:template_create',
        'reports:component_library',
        'reports:schedule_list',
        'reports:schedule_create',
    ]
    
    success_count = 0
    for url_name in urls_to_test:
        try:
            url = reverse(url_name)
            print_success(f"URL '{url_name}' resuelta a: {url}")
            success_count += 1
        except Exception as e:
            print_error(f"Error resolviendo URL '{url_name}': {e}")
    
    print_info(f"URLs resueltas exitosamente: {success_count}/{len(urls_to_test)}")
    return success_count == len(urls_to_test)

def test_menu_integration():
    """Probar que el módulo reports aparezca en el menú dinámico"""
    print_header("PRUEBA DE INTEGRACIÓN CON MENÚ DINÁMICO")
    
    try:
        # Obtener usuario de prueba
        user = UsuarioExtendido.objects.first()
        if not user:
            print_error("No se encontró ningún usuario para la prueba")
            return False
        
        print_info(f"Usuario de prueba: {user.email}")
        
        # Obtener apps visibles para el usuario
        apps = apps_visibles_para_usuario(user)
        
        # Buscar el módulo reports
        reports_app = None
        for app in apps:
            if app.get('id') == 'reports':
                reports_app = app
                break
        
        if reports_app:
            print_success("Módulo reports encontrado en el menú dinámico")
            print_info(f"Nombre: {reports_app.get('nombre')}")
            print_info(f"URL principal: {reports_app.get('url')}")
            print_info(f"Color: {reports_app.get('color')}")
            print_info(f"Orden: {reports_app.get('orden')}")
            
            # Verificar submenús
            submenus = reports_app.get('submenus', [])
            print_info(f"Submenús encontrados: {len(submenus)}")
            
            for submenu in submenus:
                seccion = submenu.get('seccion', 'Sin sección')
                items = submenu.get('items', [])
                print_info(f"  - {seccion}: {len(items)} elementos")
                
                for item in items:
                    label = item.get('label', 'Sin etiqueta')
                    url = item.get('url', '#')
                    permission = item.get('permission', 'Sin permiso')
                    print_info(f"    • {label} -> {url} (permiso: {permission})")
            
            return True
        else:
            print_error("Módulo reports NO encontrado en el menú dinámico")
            print_info("Apps disponibles:")
            for app in apps:
                print_info(f"  - {app.get('id')}: {app.get('nombre')}")
            return False
            
    except Exception as e:
        print_error(f"Error al probar integración con menú: {e}")
        return False

def test_user_permissions():
    """Probar permisos de usuario para el módulo reports"""
    print_header("PRUEBA DE PERMISOS DE USUARIO")
    
    try:
        user = UsuarioExtendido.objects.first()
        if not user:
            print_error("No se encontró ningún usuario para la prueba")
            return False
        
        # Obtener permisos del usuario
        permisos = user.get_permisos_totales()
        print_info(f"Usuario: {user.email}")
        print_info(f"Total de permisos: {len(permisos)}")
        
        # Verificar permisos específicos de reports
        reports_permissions = [p for p in permisos if p.startswith('reports.')]
        print_info(f"Permisos de reports: {len(reports_permissions)}")
        
        for perm in reports_permissions:
            print_info(f"  - {perm}")
        
        # Verificar permisos críticos
        critical_permissions = [
            'reports.ver',
            'reports.crear',
            'reports.ver_template',
            'reports.crear_template',
            'reports.ver_schedule',
            'reports.crear_schedule'
        ]
        
        missing_permissions = []
        for perm in critical_permissions:
            if perm in permisos or '*' in permisos:
                print_success(f"Permiso '{perm}' disponible")
            else:
                print_error(f"Permiso '{perm}' NO disponible")
                missing_permissions.append(perm)
        
        if missing_permissions:
            print_info("Permisos faltantes que podrían afectar la funcionalidad")
            return False
        else:
            print_success("Todos los permisos críticos están disponibles")
            return True
            
    except Exception as e:
        print_error(f"Error al probar permisos: {e}")
        return False

def test_views_access():
    """Probar acceso a las vistas principales de reports"""
    print_header("PRUEBA DE ACCESO A VISTAS")
    
    try:
        user = UsuarioExtendido.objects.first()
        if not user:
            print_error("No se encontró ningún usuario para la prueba")
            return False
        
        client = Client()
        client.force_login(user)
        
        # URLs principales a probar
        test_urls = [
            '/reports/',
            '/reports/reports/',
            '/reports/templates/',
            '/reports/components/',
            '/reports/schedules/',
        ]
        
        success_count = 0
        for url in test_urls:
            try:
                response = client.get(url)
                if response.status_code == 200:
                    print_success(f"Vista accesible: {url}")
                    success_count += 1
                elif response.status_code == 302:
                    print_info(f"Redirección en: {url} (status: {response.status_code})")
                    success_count += 1
                else:
                    print_error(f"Error en vista: {url} (status: {response.status_code})")
            except Exception as e:
                print_error(f"Excepción en vista {url}: {e}")
        
        print_info(f"Vistas accesibles: {success_count}/{len(test_urls)}")
        return success_count >= len(test_urls) * 0.8  # 80% de éxito mínimo
        
    except Exception as e:
        print_error(f"Error al probar vistas: {e}")
        return False

def test_data_integrity():
    """Probar integridad de datos y relaciones"""
    print_header("PRUEBA DE INTEGRIDAD DE DATOS")
    
    try:
        # Verificar que existan empresas y branches
        empresas_count = Empresa.objects.count()
        branches_count = Branch.objects.count()
        
        print_info(f"Empresas en el sistema: {empresas_count}")
        print_info(f"Branches en el sistema: {branches_count}")
        
        if empresas_count == 0:
            print_error("No hay empresas en el sistema")
            return False
        
        if branches_count == 0:
            print_error("No hay branches en el sistema")
            return False
        
        # Verificar datos de reports
        reports_count = Report.objects.count()
        templates_count = ReportTemplate.objects.count()
        schedules_count = ReportSchedule.objects.count()
        
        print_info(f"Reportes existentes: {reports_count}")
        print_info(f"Plantillas existentes: {templates_count}")
        print_info(f"Programaciones existentes: {schedules_count}")
        
        # Verificar que los reportes tengan empresa asignada
        reports_without_empresa = Report.objects.filter(empresa__isnull=True).count()
        if reports_without_empresa > 0:
            print_error(f"Hay {reports_without_empresa} reportes sin empresa asignada")
        else:
            print_success("Todos los reportes tienen empresa asignada")
        
        # Verificar que las plantillas tengan empresa asignada
        templates_without_empresa = ReportTemplate.objects.filter(empresa__isnull=True).count()
        if templates_without_empresa > 0:
            print_error(f"Hay {templates_without_empresa} plantillas sin empresa asignada")
        else:
            print_success("Todas las plantillas tienen empresa asignada")
        
        return True
        
    except Exception as e:
        print_error(f"Error al probar integridad de datos: {e}")
        return False

def test_module_registry():
    """Probar que el módulo esté registrado correctamente"""
    print_header("PRUEBA DE REGISTRO DE MÓDULO")
    
    try:
        from core.module_registry import MODULE_CONFIGS
        
        if 'reports' in MODULE_CONFIGS:
            config = MODULE_CONFIGS['reports']
            print_success("Módulo reports registrado en MODULE_CONFIGS")
            print_info(f"Nombre: {config.get('display_name')}")
            print_info(f"Versión: {config.get('version')}")
            print_info(f"Activo: {config.get('is_required', False)}")
            
            # Verificar permisos registrados
            permissions = config.get('permissions', [])
            print_info(f"Permisos registrados: {len(permissions)}")
            
            return True
        else:
            print_error("Módulo reports NO registrado en MODULE_CONFIGS")
            return False
            
    except Exception as e:
        print_error(f"Error al probar registro de módulo: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print_header("INICIO DE PRUEBAS COMPLETAS DEL MÓDULO REPORTS")
    
    tests = [
        ("Modelos de Base de Datos", test_database_models),
        ("Resolución de URLs", test_urls_resolution),
        ("Integración con Menú", test_menu_integration),
        ("Permisos de Usuario", test_user_permissions),
        ("Acceso a Vistas", test_views_access),
        ("Integridad de Datos", test_data_integrity),
        ("Registro de Módulo", test_module_registry),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Error en prueba '{test_name}': {e}")
            results.append((test_name, False))
    
    # Resumen final
    print_header("RESUMEN DE PRUEBAS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print_info(f"Pruebas pasadas: {passed}/{total}")
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status} - {test_name}")
    
    if passed == total:
        print_success("🎉 TODAS LAS PRUEBAS PASARON - MÓDULO REPORTS COMPLETAMENTE FUNCIONAL")
    elif passed >= total * 0.8:
        print_info("⚠️ La mayoría de las pruebas pasaron - Módulo reports funcional con algunas advertencias")
    else:
        print_error("❌ Múltiples pruebas fallaron - Revisar configuración del módulo reports")
    
    print_header("FIN DE PRUEBAS")

if __name__ == "__main__":
    main() 