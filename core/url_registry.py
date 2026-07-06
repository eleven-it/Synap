"""
Registro dinámico de URLs por módulo
Maneja la carga dinámica de URLs de módulos activos
"""

from django.urls import path, include
from django.core.exceptions import ImproperlyConfigured
from core.module_manager import module_manager


# Módulos ya montados en django_project/urls.py (evita W005 namespace duplicado).
SKIP_MODULES_IN_MAIN_URLS = frozenset(
    (
        "core",
        "login",
        "reports",
        "ia",
        "self_checkout",
        "logistica",
        "tiendanube_administranet",
        "mpr",
        "ecom",
        "odoo_migracion",
    )
)


class URLRegistry:
    """Registro dinámico de URLs por módulo"""
    
    def __init__(self):
        self.module_urls = {}
        self.load_module_urls()
    
    def load_module_urls(self):
        """Carga las URLs de los módulos activos"""
        for module_name in module_manager.get_active_modules():
            try:
                module_urls = self.get_module_urls(module_name)
                if module_urls:
                    self.module_urls[module_name] = module_urls
            except ImportError:
                # Módulo no tiene URLs definidas
                pass
            except Exception as e:
                print(f"Error loading URLs for module {module_name}: {e}")
    
    def get_module_urls(self, module_name):
        """Obtiene las URLs de un módulo específico"""
        try:
            # Intentar importar el módulo de URLs
            module = __import__(f'{module_name}.urls', fromlist=['urlpatterns'])
            return getattr(module, 'urlpatterns', [])
        except ImportError:
            # Módulo no tiene archivo urls.py
            return []
        except AttributeError:
            # Módulo no tiene urlpatterns definido
            return []
    
    def get_all_urls(self):
        """Obtiene todas las URLs de módulos activos"""
        urls = []
        for module_name, module_urls in self.module_urls.items():
            urls.extend(module_urls)
        return urls
    
    def get_module_url_patterns(self):
        """Obtiene los patrones de URL para incluir en el archivo principal.
        No incluye módulos que ya están en urls.py principal (evita W005 namespace duplicado).
        """
        url_patterns = []
        skip_in_main = SKIP_MODULES_IN_MAIN_URLS

        for module_name, module_urls in self.module_urls.items():
            if module_name in skip_in_main or not module_urls:
                continue
            url_patterns.append(
                path(f'{module_name}/', include((f'{module_name}.urls', module_name), namespace=module_name))
            )

        return url_patterns
    
    def reload_module_urls(self):
        """Recarga las URLs de módulos"""
        self.module_urls = {}
        self.load_module_urls()
    
    def get_module_url_info(self, module_name):
        """Obtiene información sobre las URLs de un módulo"""
        if module_name not in self.module_urls:
            return None
        
        urls = self.module_urls[module_name]
        
        info = {
            'module': module_name,
            'url_count': len(urls),
            'urls': []
        }
        
        for url in urls:
            url_info = {
                'pattern': str(url.pattern),
                'name': getattr(url, 'name', None),
                'callback': getattr(url, 'callback', None),
            }
            info['urls'].append(url_info)
        
        return info
    
    def validate_module_urls(self, module_name):
        """Valida las URLs de un módulo"""
        try:
            urls = self.get_module_urls(module_name)
            
            # Verificar que las URLs sean válidas
            for url in urls:
                if not hasattr(url, 'pattern'):
                    return False, f"URL pattern missing in {module_name}"
                
                # Verificar nombres duplicados
                if hasattr(url, 'name') and url.name:
                    # Aquí se podría agregar validación de nombres únicos
                    pass
            
            return True, f"URLs válidas para {module_name}"
            
        except Exception as e:
            return False, f"Error validando URLs de {module_name}: {str(e)}"
    
    def get_url_by_name(self, url_name):
        """Busca una URL por nombre en todos los módulos activos"""
        for module_name, module_urls in self.module_urls.items():
            for url in module_urls:
                if hasattr(url, 'name') and url.name == url_name:
                    return {
                        'module': module_name,
                        'url': url,
                        'pattern': str(url.pattern)
                    }
        return None
    
    def get_module_urls_summary(self):
        """Obtiene un resumen de todas las URLs de módulos"""
        summary = {
            'total_modules': len(self.module_urls),
            'total_urls': 0,
            'modules': []
        }
        
        for module_name, module_urls in self.module_urls.items():
            module_info = {
                'name': module_name,
                'url_count': len(module_urls),
                'urls': []
            }
            
            for url in module_urls:
                url_info = {
                    'pattern': str(url.pattern),
                    'name': getattr(url, 'name', None),
                }
                module_info['urls'].append(url_info)
            
            summary['modules'].append(module_info)
            summary['total_urls'] += len(module_urls)
        
        return summary


class DynamicURLPattern:
    """Patrón de URL dinámico que se puede activar/desactivar"""
    
    def __init__(self, pattern, view, name=None, module=None):
        self.pattern = pattern
        self.view = view
        self.name = name
        self.module = module
        self.is_active = True
    
    def __str__(self):
        return f"{self.module}:{self.name}" if self.name else str(self.pattern)
    
    def activate(self):
        """Activa el patrón de URL"""
        self.is_active = True
    
    def deactivate(self):
        """Desactiva el patrón de URL"""
        self.is_active = False


class ModuleURLManager:
    """Gestor avanzado de URLs de módulos con funcionalidades adicionales"""
    
    def __init__(self):
        self.registry = URLRegistry()
        self.dynamic_patterns = {}
    
    def register_dynamic_pattern(self, module_name, pattern, view, name=None):
        """Registra un patrón de URL dinámico"""
        if module_name not in self.dynamic_patterns:
            self.dynamic_patterns[module_name] = []
        
        dynamic_pattern = DynamicURLPattern(pattern, view, name, module_name)
        self.dynamic_patterns[module_name].append(dynamic_pattern)
        
        return dynamic_pattern
    
    def get_active_patterns(self, module_name):
        """Obtiene los patrones activos de un módulo"""
        patterns = []
        
        # URLs estáticas del módulo
        if module_name in self.registry.module_urls:
            patterns.extend(self.registry.module_urls[module_name])
        
        # URLs dinámicas del módulo
        if module_name in self.dynamic_patterns:
            for pattern in self.dynamic_patterns[module_name]:
                if pattern.is_active:
                    patterns.append(path(pattern.pattern, pattern.view, name=pattern.name))
        
        return patterns
    
    def activate_module_patterns(self, module_name):
        """Activa todos los patrones de un módulo"""
        if module_name in self.dynamic_patterns:
            for pattern in self.dynamic_patterns[module_name]:
                pattern.activate()
    
    def deactivate_module_patterns(self, module_name):
        """Desactiva todos los patrones de un módulo"""
        if module_name in self.dynamic_patterns:
            for pattern in self.dynamic_patterns[module_name]:
                pattern.deactivate()
    
    def get_all_active_patterns(self):
        """Obtiene todos los patrones activos"""
        all_patterns = []
        
        for module_name in module_manager.get_active_modules():
            patterns = self.get_active_patterns(module_name)
            all_patterns.extend(patterns)
        
        return all_patterns


# Instancia global del registro de URLs
url_registry = URLRegistry()
url_manager = ModuleURLManager() 