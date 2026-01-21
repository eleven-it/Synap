"""
Gestor de hooks y eventos entre módulos del sistema Synap
Maneja la comunicación y extensibilidad entre módulos mediante hooks
"""

import inspect
from typing import Dict, List, Callable, Any, Optional
from django.core.cache import cache
from core.module_manager import module_manager


class HookManager:
    """Gestor de hooks y eventos entre módulos"""
    
    def __init__(self):
        self.hooks = {}
        self.event_listeners = {}
        self.hook_registry = {}
        self.load_hooks()
    
    def load_hooks(self):
        """Carga los hooks de todos los módulos activos"""
        for module_name in module_manager.get_active_modules():
            try:
                hooks = self.get_module_hooks(module_name)
                if hooks:
                    self.hook_registry[module_name] = hooks
            except ImportError:
                # Módulo no tiene configuración de hooks
                pass
            except Exception as e:
                print(f"Error loading hooks for module {module_name}: {e}")
    
    def get_module_hooks(self, module_name):
        """Obtiene la configuración de hooks de un módulo"""
        try:
            module = __import__(f'{module_name}.hooks', fromlist=['HOOKS'])
            return getattr(module, 'HOOKS', {})
        except ImportError:
            # Módulo no tiene archivo hooks.py
            return {}
        except AttributeError:
            # Módulo no tiene HOOKS definido
            return {}
    
    def register_hook(self, hook_name: str, callback: Callable, module_name: str = None, priority: int = 10):
        """
        Registra un hook con su callback
        
        Args:
            hook_name: Nombre del hook
            callback: Función a ejecutar
            module_name: Nombre del módulo (opcional)
            priority: Prioridad de ejecución (menor = mayor prioridad)
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        
        hook_info = {
            'callback': callback,
            'module_name': module_name,
            'priority': priority,
            'function_name': callback.__name__,
            'module': callback.__module__
        }
        
        self.hooks[hook_name].append(hook_info)
        # Ordenar por prioridad
        self.hooks[hook_name].sort(key=lambda x: x['priority'])
    
    def unregister_hook(self, hook_name: str, callback: Callable):
        """Desregistra un hook específico"""
        if hook_name in self.hooks:
            self.hooks[hook_name] = [
                hook for hook in self.hooks[hook_name] 
                if hook['callback'] != callback
            ]
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Ejecuta todos los hooks registrados para un nombre específico
        
        Returns:
            Lista de resultados de todos los hooks ejecutados
        """
        results = []
        
        if hook_name not in self.hooks:
            return results
        
        for hook_info in self.hooks[hook_name]:
            try:
                result = hook_info['callback'](*args, **kwargs)
                results.append({
                    'module': hook_info['module_name'],
                    'function': hook_info['function_name'],
                    'result': result,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'module': hook_info['module_name'],
                    'function': hook_info['function_name'],
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def execute_hook_chain(self, hook_name: str, initial_value: Any = None, *args, **kwargs) -> Any:
        """
        Ejecuta hooks en cadena, pasando el resultado de uno al siguiente
        
        Args:
            hook_name: Nombre del hook
            initial_value: Valor inicial para la cadena
            *args, **kwargs: Argumentos adicionales
            
        Returns:
            Resultado final de la cadena de hooks
        """
        current_value = initial_value
        
        if hook_name not in self.hooks:
            return current_value
        
        for hook_info in self.hooks[hook_name]:
            try:
                # Pasar el valor actual como primer argumento
                if current_value is not None:
                    result = hook_info['callback'](current_value, *args, **kwargs)
                else:
                    result = hook_info['callback'](*args, **kwargs)
                
                current_value = result
                
            except Exception as e:
                print(f"Error in hook chain {hook_name}: {e}")
                # Continuar con el siguiente hook
                continue
        
        return current_value
    
    def register_event_listener(self, event_name: str, callback: Callable, module_name: str = None):
        """Registra un listener para un evento específico"""
        if event_name not in self.event_listeners:
            self.event_listeners[event_name] = []
        
        listener_info = {
            'callback': callback,
            'module_name': module_name,
            'function_name': callback.__name__,
            'module': callback.__module__
        }
        
        self.event_listeners[event_name].append(listener_info)
    
    def emit_event(self, event_name: str, *args, **kwargs):
        """Emite un evento a todos los listeners registrados"""
        if event_name not in self.event_listeners:
            return
        
        for listener_info in self.event_listeners[event_name]:
            try:
                listener_info['callback'](*args, **kwargs)
            except Exception as e:
                print(f"Error in event listener {event_name}: {e}")
    
    def get_hook_info(self, hook_name: str = None) -> Dict:
        """Obtiene información sobre hooks registrados"""
        if hook_name:
            return {
                'hook_name': hook_name,
                'listeners': self.hooks.get(hook_name, [])
            }
        
        return {
            'total_hooks': len(self.hooks),
            'hooks': list(self.hooks.keys()),
            'hook_details': {
                name: len(listeners) for name, listeners in self.hooks.items()
            }
        }
    
    def get_event_info(self, event_name: str = None) -> Dict:
        """Obtiene información sobre eventos registrados"""
        if event_name:
            return {
                'event_name': event_name,
                'listeners': self.event_listeners.get(event_name, [])
            }
        
        return {
            'total_events': len(self.event_listeners),
            'events': list(self.event_listeners.keys()),
            'event_details': {
                name: len(listeners) for name, listeners in self.event_listeners.items()
            }
        }
    
    def validate_hooks(self) -> List[Dict]:
        """Valida la configuración de hooks"""
        results = []
        
        for module_name, hooks_config in self.hook_registry.items():
            for hook_name, hook_config in hooks_config.items():
                # Verificar que el hook esté registrado
                if hook_name not in self.hooks:
                    results.append({
                        'type': 'warning',
                        'module': module_name,
                        'hook': hook_name,
                        'message': f'Hook {hook_name} not registered'
                    })
                else:
                    results.append({
                        'type': 'success',
                        'module': module_name,
                        'hook': hook_name,
                        'message': f'Hook {hook_name} registered with {len(self.hooks[hook_name])} listeners'
                    })
        
        return results
    
    def reload_hooks(self):
        """Recarga todos los hooks"""
        self.hooks = {}
        self.event_listeners = {}
        self.hook_registry = {}
        self.load_hooks()
    
    def get_module_hooks_summary(self, module_name: str) -> Dict:
        """Obtiene un resumen de hooks de un módulo específico"""
        module_hooks = self.hook_registry.get(module_name, {})
        
        summary = {
            'module_name': module_name,
            'total_hooks': len(module_hooks),
            'hooks': list(module_hooks.keys()),
            'registered_listeners': 0
        }
        
        # Contar listeners registrados para este módulo
        for hook_name, listeners in self.hooks.items():
            for listener in listeners:
                if listener['module_name'] == module_name:
                    summary['registered_listeners'] += 1
        
        return summary
    
    def cleanup_module_hooks(self, module_name: str):
        """Limpia todos los hooks de un módulo específico"""
        # Remover hooks del módulo
        for hook_name in list(self.hooks.keys()):
            self.hooks[hook_name] = [
                hook for hook in self.hooks[hook_name] 
                if hook['module_name'] != module_name
            ]
            
            # Remover hook si no tiene listeners
            if not self.hooks[hook_name]:
                del self.hooks[hook_name]
        
        # Remover event listeners del módulo
        for event_name in list(self.event_listeners.keys()):
            self.event_listeners[event_name] = [
                listener for listener in self.event_listeners[event_name] 
                if listener['module_name'] != module_name
            ]
            
            # Remover evento si no tiene listeners
            if not self.event_listeners[event_name]:
                del self.event_listeners[event_name]
        
        # Remover del registro
        if module_name in self.hook_registry:
            del self.hook_registry[module_name]


# Instancia global del HookManager
hook_manager = HookManager() 