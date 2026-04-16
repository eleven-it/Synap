"""
Gestor central de módulos del sistema Synap
Maneja la activación, desactivación y gestión de dependencias de módulos
"""

from django.apps import apps as django_apps
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from .module_registry import MODULE_CONFIGS
from .models import ModuleConfig


class ModuleManager:
    """Gestor central de módulos del sistema"""

    ACTIVE_MODULES_CACHE_KEY = "core.active_modules.db"
    ACTIVE_MODULES_CACHE_TTL = 300
    
    def __init__(self):
        self.modules = {}
        self.active_modules = set()
        self.load_modules()
    
    def load_modules(self):
        """Carga la configuración de módulos desde la base de datos"""
        try:
            self.active_modules = {
                config.name for config in ModuleConfig.objects.filter(is_active=True)
            }
            cache.set(
                self.ACTIVE_MODULES_CACHE_KEY,
                sorted(self.active_modules),
                self.ACTIVE_MODULES_CACHE_TTL,
            )
        except Exception as e:
            # Si hay error al cargar desde DB, usar configuración por defecto
            print(f"Error loading modules from DB: {e}")
            self._load_default_modules()
    
    def _load_default_modules(self):
        """Carga módulos por defecto (core, login, dashboard)"""
        self.active_modules = {'core', 'login', 'dashboard'}
        cache.set(
            self.ACTIVE_MODULES_CACHE_KEY,
            sorted(self.active_modules),
            self.ACTIVE_MODULES_CACHE_TTL,
        )

    def _refresh_active_modules_from_cache_or_db(self, force=False):
        """Sincroniza módulos activos desde cache/DB para evitar estado stale en procesos vivos."""
        if force:
            cache.delete(self.ACTIVE_MODULES_CACHE_KEY)

        cached = cache.get(self.ACTIVE_MODULES_CACHE_KEY)
        if cached is not None:
            self.active_modules = set(cached)
            return self.active_modules

        try:
            self.active_modules = {
                config.name for config in ModuleConfig.objects.filter(is_active=True)
            }
        except Exception:
            self._load_default_modules()
            return self.active_modules

        cache.set(
            self.ACTIVE_MODULES_CACHE_KEY,
            sorted(self.active_modules),
            self.ACTIVE_MODULES_CACHE_TTL,
        )
        return self.active_modules

    @staticmethod
    def _django_app_installed(module_name):
        """
        El nombre de módulo en MODULE_CONFIGS coincide con el app_label de Django.
        Si la app no está en INSTALLED_APPS, no se deben cargar URLs/hooks ni tratar
        el módulo como operativo (p. ej. tiendanube_administranet comentado en settings).
        """
        try:
            return django_apps.is_installed(module_name)
        except Exception:
            return False
    
    def is_module_active(self, module_name):
        """Verifica si un módulo está activo y su app Django está instalada."""
        self._refresh_active_modules_from_cache_or_db()
        return (
            module_name in self.active_modules
            and self._django_app_installed(module_name)
        )
    
    def get_active_modules(self):
        """Retorna la lista de módulos activos (solo apps presentes en INSTALLED_APPS)."""
        self._refresh_active_modules_from_cache_or_db()
        return sorted(
            m for m in self.active_modules if self._django_app_installed(m)
        )
    
    def get_all_modules(self):
        """Retorna todos los módulos disponibles"""
        return list(MODULE_CONFIGS.keys())
    
    def get_module_config(self, module_name):
        """Obtiene la configuración de un módulo"""
        return MODULE_CONFIGS.get(module_name, {})
    
    def can_activate_module(self, module_name):
        """Verifica si se puede activar un módulo"""
        if module_name not in MODULE_CONFIGS:
            return False
        
        config = MODULE_CONFIGS[module_name]
        dependencies = config.get('dependencies', [])
        
        # Verificar que todas las dependencias estén activas
        for dep in dependencies:
            if not self.is_module_active(dep):
                return False
        
        return True
    
    def can_deactivate_module(self, module_name):
        """Verifica si se puede desactivar un módulo"""
        if module_name not in MODULE_CONFIGS:
            return False
        
        config = MODULE_CONFIGS[module_name]
        
        # No se puede desactivar módulos core o requeridos
        if config.get('is_core', False) or config.get('is_required', False):
            return False
        
        # Verificar si otros módulos dependen de este
        dependents = self.get_module_dependents(module_name)
        if dependents:
            return False
        
        return True
    
    def activate_module(self, module_name, user=None):
        """Activa un módulo"""
        if not self.can_activate_module(module_name):
            return False, f"No se puede activar el módulo {module_name}"
        
        try:
            with transaction.atomic():
                # Crear o actualizar configuración en DB
                config, created = ModuleConfig.objects.get_or_create(
                    name=module_name,
                    defaults={
                        'display_name': MODULE_CONFIGS[module_name]['display_name'],
                        'description': MODULE_CONFIGS[module_name]['description'],
                        'version': MODULE_CONFIGS[module_name]['version'],
                        'author': MODULE_CONFIGS[module_name].get('author', ''),
                        'is_required': MODULE_CONFIGS[module_name].get('is_required', False),
                        'is_core': MODULE_CONFIGS[module_name].get('is_core', False),
                        'dependencies': MODULE_CONFIGS[module_name].get('dependencies', []),
                        'optional_dependencies': MODULE_CONFIGS[module_name].get('optional_dependencies', []),
                        'settings': MODULE_CONFIGS[module_name].get('settings', {}),
                        'permissions': MODULE_CONFIGS[module_name].get('permissions', []),
                        'hooks': MODULE_CONFIGS[module_name].get('hooks', []),
                        'is_active': True,
                        'last_activated': timezone.now(),
                    }
                )
                
                if not created:
                    config.is_active = True
                    config.last_activated = timezone.now()
                    config.save()
                
                # Recargar módulos activos desde la base de datos
                self.load_modules()
                
                # Ejecutar hooks de activación
                self._execute_module_hooks(module_name, 'module_activated', user=user)
                
                # Limpiar cache
                self._clear_cache()
                
                return True, f"Módulo {module_name} activado correctamente"
                
        except Exception as e:
            return False, f"Error al activar módulo {module_name}: {str(e)}"
    
    def deactivate_module(self, module_name, user=None):
        """Desactiva un módulo"""
        if not self.can_deactivate_module(module_name):
            return False, f"No se puede desactivar el módulo {module_name}"
        
        try:
            with transaction.atomic():
                # Actualizar configuración en DB
                config = ModuleConfig.objects.get(name=module_name)
                config.is_active = False
                config.last_deactivated = timezone.now()
                config.save()
                
                # Recargar módulos activos desde la base de datos
                self.load_modules()
                
                # Ejecutar hooks de desactivación
                self._execute_module_hooks(module_name, 'module_deactivated', user=user)
                
                # Limpiar cache
                self._clear_cache()
                
                return True, f"Módulo {module_name} desactivado correctamente"
                
        except Exception as e:
            return False, f"Error al desactivar módulo {module_name}: {str(e)}"
    
    def get_module_dependencies(self, module_name):
        """Obtiene las dependencias de un módulo"""
        if module_name in MODULE_CONFIGS:
            return MODULE_CONFIGS[module_name].get('dependencies', [])
        return []
    
    def get_module_dependents(self, module_name):
        """Obtiene los módulos que dependen de este"""
        dependents = []
        for module, config in MODULE_CONFIGS.items():
            dependencies = config.get('dependencies', [])
            if module_name in dependencies and self.is_module_active(module):
                dependents.append(module)
        return dependents
    
    def get_activation_order(self, modules_to_activate):
        """Obtiene el orden correcto para activar módulos"""
        order = []
        visited = set()
        
        def visit(module):
            if module in visited:
                return
            visited.add(module)
            
            if module in MODULE_CONFIGS:
                for dep in MODULE_CONFIGS[module].get('dependencies', []):
                    visit(dep)
            
            order.append(module)
        
        for module in modules_to_activate:
            visit(module)
        
        return order
    
    def check_circular_dependencies(self):
        """Verifica dependencias circulares"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(module):
            visited.add(module)
            rec_stack.add(module)
            
            if module in MODULE_CONFIGS:
                for dep in MODULE_CONFIGS[module].get('dependencies', []):
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(module)
            return False
        
        for module in MODULE_CONFIGS.keys():
            if module not in visited:
                if has_cycle(module):
                    return True
        
        return False
    
    def get_module_status(self, module_name):
        """Obtiene el estado completo de un módulo"""
        if module_name not in MODULE_CONFIGS:
            return None
        
        config = MODULE_CONFIGS[module_name]
        is_active = self.is_module_active(module_name)
        
        return {
            'name': module_name,
            'display_name': config['display_name'],
            'description': config['description'],
            'version': config['version'],
            'is_active': is_active,
            'is_required': config.get('is_required', False),
            'is_core': config.get('is_core', False),
            'dependencies': config.get('dependencies', []),
            'optional_dependencies': config.get('optional_dependencies', []),
            'can_activate': self.can_activate_module(module_name),
            'can_deactivate': self.can_deactivate_module(module_name),
            'dependents': self.get_module_dependents(module_name),
            'missing_dependencies': self._get_missing_dependencies(module_name),
        }
    
    def _get_missing_dependencies(self, module_name):
        """Obtiene las dependencias faltantes de un módulo"""
        if module_name not in MODULE_CONFIGS:
            return []
        
        dependencies = MODULE_CONFIGS[module_name].get('dependencies', [])
        missing = []
        
        for dep in dependencies:
            if not self.is_module_active(dep):
                missing.append(dep)
        
        return missing
    
    def _execute_module_hooks(self, module_name, hook_name, **kwargs):
        """Ejecuta hooks de un módulo específico"""
        try:
            # Intentar importar y ejecutar hooks del módulo
            module = __import__(f'{module_name}.hooks', fromlist=['HOOKS'])
            hooks = getattr(module, 'HOOKS', {})
            
            if hook_name in hooks:
                hooks[hook_name](**kwargs)
        except ImportError:
            # Módulo no tiene hooks definidos
            pass
        except Exception as e:
            # Log error pero no fallar
            print(f"Error executing hook {hook_name} for module {module_name}: {e}")
    
    def _clear_cache(self):
        """Limpia el cache relacionado con módulos"""
        cache_keys = [
            'active_modules',
            'module_configs',
            'module_dependencies',
            self.ACTIVE_MODULES_CACHE_KEY,
        ]
        
        for key in cache_keys:
            cache.delete(key)
    
    def get_modules_summary(self):
        """Obtiene un resumen de todos los módulos"""
        summary = {
            'total_modules': len(MODULE_CONFIGS),
            'active_modules': len(self.active_modules),
            'core_modules': 0,
            'required_modules': 0,
            'optional_modules': 0,
            'modules': []
        }
        
        for module_name in MODULE_CONFIGS.keys():
            config = MODULE_CONFIGS[module_name]
            status = self.get_module_status(module_name)
            
            if config.get('is_core', False):
                summary['core_modules'] += 1
            elif config.get('is_required', False):
                summary['required_modules'] += 1
            else:
                summary['optional_modules'] += 1
            
            summary['modules'].append(status)
        
        return summary


# Instancia global del ModuleManager
module_manager = ModuleManager() 