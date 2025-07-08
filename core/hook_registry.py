"""
Registro de hooks del sistema Synap
Gestiona el registro y descubrimiento de hooks de manera centralizada
"""

import inspect
from typing import Dict, List, Callable, Any, Optional, Type
from django.core.cache import cache
from core.hook_manager import hook_manager
from core.module_events import EventHandler, EventFilter


class HookRegistry:
    """Registro centralizado de hooks del sistema"""
    
    def __init__(self):
        self.registered_hooks = {}
        self.hook_metadata = {}
        self.hook_dependencies = {}
        self.hook_validators = {}
        self.load_registry()
    
    def load_registry(self):
        """Carga el registro de hooks desde todos los módulos activos"""
        from core.module_manager import module_manager
        
        for module_name in module_manager.get_active_modules():
            try:
                registry_data = self.get_module_hook_registry(module_name)
                if registry_data:
                    self.register_module_hooks(module_name, registry_data)
            except ImportError:
                # Módulo no tiene configuración de hook registry
                pass
            except Exception as e:
                print(f"Error loading hook registry for module {module_name}: {e}")
    
    def get_module_hook_registry(self, module_name):
        """Obtiene el registro de hooks de un módulo"""
        try:
            module = __import__(f'{module_name}.hook_registry', fromlist=['HOOK_REGISTRY'])
            return getattr(module, 'HOOK_REGISTRY', {})
        except ImportError:
            # Módulo no tiene archivo hook_registry.py
            return {}
        except AttributeError:
            # Módulo no tiene HOOK_REGISTRY definido
            return {}
    
    def register_module_hooks(self, module_name: str, registry_data: Dict):
        """Registra hooks de un módulo"""
        for hook_name, hook_config in registry_data.items():
            self.register_hook(
                hook_name=hook_name,
                callback=hook_config.get('callback'),
                module_name=module_name,
                priority=hook_config.get('priority', 10),
                description=hook_config.get('description', ''),
                dependencies=hook_config.get('dependencies', []),
                validator=hook_config.get('validator'),
                metadata=hook_config.get('metadata', {})
            )
    
    def register_hook(self, hook_name: str, callback: Callable, module_name: str = None,
                     priority: int = 10, description: str = '', dependencies: List[str] = None,
                     validator: Callable = None, metadata: Dict = None):
        """
        Registra un hook en el registro
        
        Args:
            hook_name: Nombre del hook
            callback: Función callback
            module_name: Nombre del módulo
            priority: Prioridad de ejecución
            description: Descripción del hook
            dependencies: Dependencias del hook
            validator: Función validadora
            metadata: Metadatos adicionales
        """
        if hook_name not in self.registered_hooks:
            self.registered_hooks[hook_name] = []
            self.hook_metadata[hook_name] = {
                'description': description,
                'total_registrations': 0,
                'modules': set()
            }
            self.hook_dependencies[hook_name] = dependencies or []
            self.hook_validators[hook_name] = validator
        
        hook_info = {
            'callback': callback,
            'module_name': module_name,
            'priority': priority,
            'function_name': callback.__name__,
            'module': callback.__module__,
            'description': description,
            'metadata': metadata or {}
        }
        
        self.registered_hooks[hook_name].append(hook_info)
        self.registered_hooks[hook_name].sort(key=lambda x: x['priority'])
        
        # Actualizar metadatos
        self.hook_metadata[hook_name]['total_registrations'] += 1
        if module_name:
            self.hook_metadata[hook_name]['modules'].add(module_name)
        
        # Registrar en el hook manager
        hook_manager.register_hook(hook_name, callback, module_name, priority)
    
    def unregister_hook(self, hook_name: str, callback: Callable):
        """Desregistra un hook específico"""
        if hook_name in self.registered_hooks:
            # Remover del registro
            self.registered_hooks[hook_name] = [
                hook for hook in self.registered_hooks[hook_name] 
                if hook['callback'] != callback
            ]
            
            # Actualizar metadatos
            if self.registered_hooks[hook_name]:
                self.hook_metadata[hook_name]['total_registrations'] = len(self.registered_hooks[hook_name])
            else:
                # Remover hook si no tiene registros
                del self.registered_hooks[hook_name]
                del self.hook_metadata[hook_name]
                if hook_name in self.hook_dependencies:
                    del self.hook_dependencies[hook_name]
                if hook_name in self.hook_validators:
                    del self.hook_validators[hook_name]
        
        # Desregistrar del hook manager
        hook_manager.unregister_hook(hook_name, callback)
    
    def get_hook_info(self, hook_name: str) -> Dict:
        """Obtiene información detallada de un hook"""
        if hook_name not in self.registered_hooks:
            return {}
        
        hook_list = self.registered_hooks[hook_name]
        metadata = self.hook_metadata[hook_name]
        
        return {
            'name': hook_name,
            'description': metadata['description'],
            'total_registrations': metadata['total_registrations'],
            'modules': list(metadata['modules']),
            'dependencies': self.hook_dependencies.get(hook_name, []),
            'has_validator': self.hook_validators.get(hook_name) is not None,
            'registrations': [
                {
                    'module_name': hook['module_name'],
                    'function_name': hook['function_name'],
                    'priority': hook['priority'],
                    'description': hook['description']
                }
                for hook in hook_list
            ]
        }
    
    def get_all_hooks(self) -> Dict:
        """Obtiene información de todos los hooks registrados"""
        return {
            hook_name: self.get_hook_info(hook_name)
            for hook_name in self.registered_hooks.keys()
        }
    
    def get_module_hooks(self, module_name: str) -> List[Dict]:
        """Obtiene todos los hooks de un módulo específico"""
        module_hooks = []
        
        for hook_name, hook_list in self.registered_hooks.items():
            for hook in hook_list:
                if hook['module_name'] == module_name:
                    module_hooks.append({
                        'hook_name': hook_name,
                        'function_name': hook['function_name'],
                        'priority': hook['priority'],
                        'description': hook['description']
                    })
        
        return module_hooks
    
    def validate_hook_registration(self, hook_name: str, callback: Callable, **kwargs) -> bool:
        """Valida el registro de un hook"""
        validator = self.hook_validators.get(hook_name)
        if validator:
            try:
                return validator(callback, **kwargs)
            except Exception as e:
                print(f"Error validating hook {hook_name}: {e}")
                return False
        return True
    
    def check_hook_dependencies(self, hook_name: str) -> List[str]:
        """Verifica las dependencias de un hook"""
        dependencies = self.hook_dependencies.get(hook_name, [])
        missing_dependencies = []
        
        for dep in dependencies:
            if dep not in self.registered_hooks:
                missing_dependencies.append(dep)
        
        return missing_dependencies
    
    def get_hook_statistics(self) -> Dict:
        """Obtiene estadísticas del registro de hooks"""
        total_hooks = len(self.registered_hooks)
        total_registrations = sum(
            metadata['total_registrations'] 
            for metadata in self.hook_metadata.values()
        )
        
        module_counts = {}
        for metadata in self.hook_metadata.values():
            for module in metadata['modules']:
                module_counts[module] = module_counts.get(module, 0) + 1
        
        return {
            'total_hooks': total_hooks,
            'total_registrations': total_registrations,
            'average_registrations_per_hook': total_registrations / total_hooks if total_hooks > 0 else 0,
            'modules_with_hooks': len(module_counts),
            'module_hook_counts': module_counts
        }
    
    def reload_registry(self):
        """Recarga el registro completo"""
        self.registered_hooks = {}
        self.hook_metadata = {}
        self.hook_dependencies = {}
        self.hook_validators = {}
        self.load_registry()
    
    def cleanup_module_hooks(self, module_name: str):
        """Limpia todos los hooks de un módulo específico"""
        hooks_to_remove = []
        
        for hook_name, hook_list in self.registered_hooks.items():
            for hook in hook_list:
                if hook['module_name'] == module_name:
                    hooks_to_remove.append((hook_name, hook['callback']))
        
        # Remover hooks
        for hook_name, callback in hooks_to_remove:
            self.unregister_hook(hook_name, callback)
    
    def export_registry(self) -> Dict:
        """Exporta el registro completo"""
        return {
            'hooks': self.get_all_hooks(),
            'statistics': self.get_hook_statistics(),
            'metadata': self.hook_metadata,
            'dependencies': self.hook_dependencies
        }
    
    def import_registry(self, registry_data: Dict):
        """Importa un registro"""
        # Limpiar registro actual
        self.registered_hooks = {}
        self.hook_metadata = {}
        self.hook_dependencies = {}
        self.hook_validators = {}
        
        # Importar datos
        if 'hooks' in registry_data:
            for hook_name, hook_info in registry_data['hooks'].items():
                self.hook_metadata[hook_name] = {
                    'description': hook_info.get('description', ''),
                    'total_registrations': hook_info.get('total_registrations', 0),
                    'modules': set(hook_info.get('modules', []))
                }
        
        if 'dependencies' in registry_data:
            self.hook_dependencies = registry_data['dependencies']


# Instancia global del HookRegistry
hook_registry = HookRegistry() 