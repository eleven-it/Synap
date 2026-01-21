"""
Event Listeners del sistema Synap
Maneja listeners de eventos de manera asíncrona y distribuida
"""

import asyncio
import threading
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import transaction
from core.module_events import EventHandler, EventFilter, EventPriority


class EventListener:
    """Listener de eventos individual"""
    
    def __init__(self, event_name: str, callback: Callable, module_name: str = None,
                 priority: EventPriority = EventPriority.NORMAL, async_execution: bool = True,
                 retry_on_failure: bool = False, max_retries: int = 3):
        self.event_name = event_name
        self.callback = callback
        self.module_name = module_name
        self.priority = priority
        self.async_execution = async_execution
        self.retry_on_failure = retry_on_failure
        self.max_retries = max_retries
        self.execution_count = 0
        self.last_execution = None
        self.error_count = 0
        self.last_error = None
    
    def execute(self, event_data: Dict) -> Dict:
        """Ejecuta el listener"""
        start_time = datetime.now()
        self.execution_count += 1
        
        try:
            if self.async_execution:
                # Ejecución asíncrona
                result = self._execute_async(event_data)
            else:
                # Ejecución síncrona
                result = self._execute_sync(event_data)
            
            self.last_execution = datetime.now()
            self.error_count = 0
            self.last_error = None
            
            return {
                'success': True,
                'result': result,
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'execution_count': self.execution_count
            }
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            
            if self.retry_on_failure and self.error_count <= self.max_retries:
                # Reintentar
                return self._retry_execution(event_data)
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'execution_count': self.execution_count,
                'error_count': self.error_count
            }
    
    def _execute_sync(self, event_data: Dict) -> Any:
        """Ejecuta el listener de forma síncrona"""
        return self.callback(event_data)
    
    def _execute_async(self, event_data: Dict) -> Any:
        """Ejecuta el listener de forma asíncrona"""
        # Crear un nuevo thread para ejecución asíncrona
        result_container = {'result': None, 'exception': None}
        
        def async_execution():
            try:
                result_container['result'] = self.callback(event_data)
            except Exception as e:
                result_container['exception'] = e
        
        thread = threading.Thread(target=async_execution)
        thread.daemon = True
        thread.start()
        thread.join(timeout=30)  # Timeout de 30 segundos
        
        if result_container['exception']:
            raise result_container['exception']
        
        return result_container['result']
    
    def _retry_execution(self, event_data: Dict) -> Dict:
        """Reintenta la ejecución del listener"""
        import time
        time.sleep(1)  # Esperar 1 segundo antes de reintentar
        return self.execute(event_data)
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del listener"""
        return {
            'event_name': self.event_name,
            'module_name': self.module_name,
            'priority': self.priority.value,
            'execution_count': self.execution_count,
            'error_count': self.error_count,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'last_error': self.last_error,
            'async_execution': self.async_execution,
            'retry_on_failure': self.retry_on_failure
        }


class EventListenerManager:
    """Gestor de event listeners"""
    
    def __init__(self):
        self.listeners = {}
        self.listener_stats = {}
        self.event_filters = {}
        self.load_listeners()
    
    def load_listeners(self):
        """Carga los listeners de todos los módulos activos"""
        from core.module_manager import module_manager
        
        for module_name in module_manager.get_active_modules():
            try:
                listeners = self.get_module_listeners(module_name)
                if listeners:
                    self.register_module_listeners(module_name, listeners)
            except ImportError:
                # Módulo no tiene configuración de listeners
                pass
            except Exception as e:
                print(f"Error loading listeners for module {module_name}: {e}")
    
    def get_module_listeners(self, module_name):
        """Obtiene los listeners de un módulo"""
        try:
            module = __import__(f'{module_name}.listeners', fromlist=['EVENT_LISTENERS'])
            return getattr(module, 'EVENT_LISTENERS', {})
        except ImportError:
            # Módulo no tiene archivo listeners.py
            return {}
        except AttributeError:
            # Módulo no tiene EVENT_LISTENERS definido
            return {}
    
    def register_module_listeners(self, module_name: str, listeners_config: Dict):
        """Registra listeners de un módulo"""
        for event_name, listener_config in listeners_config.items():
            if isinstance(listener_config, dict):
                # Configuración completa
                callback = listener_config.get('callback')
                priority = EventPriority(listener_config.get('priority', 'normal'))
                async_execution = listener_config.get('async', True)
                retry_on_failure = listener_config.get('retry_on_failure', False)
                max_retries = listener_config.get('max_retries', 3)
            else:
                # Solo callback
                callback = listener_config
                priority = EventPriority.NORMAL
                async_execution = True
                retry_on_failure = False
                max_retries = 3
            
            if callback:
                self.register_listener(
                    event_name=event_name,
                    callback=callback,
                    module_name=module_name,
                    priority=priority,
                    async_execution=async_execution,
                    retry_on_failure=retry_on_failure,
                    max_retries=max_retries
                )
    
    def register_listener(self, event_name: str, callback: Callable, module_name: str = None,
                         priority: EventPriority = EventPriority.NORMAL, async_execution: bool = True,
                         retry_on_failure: bool = False, max_retries: int = 3):
        """Registra un event listener"""
        if event_name not in self.listeners:
            self.listeners[event_name] = []
            self.listener_stats[event_name] = {
                'total_listeners': 0,
                'modules': set(),
                'execution_count': 0,
                'error_count': 0
            }
        
        listener = EventListener(
            event_name=event_name,
            callback=callback,
            module_name=module_name,
            priority=priority,
            async_execution=async_execution,
            retry_on_failure=retry_on_failure,
            max_retries=max_retries
        )
        
        self.listeners[event_name].append(listener)
        # Ordenar por prioridad
        self.listeners[event_name].sort(key=lambda x: x.priority.value)
        
        # Actualizar estadísticas
        self.listener_stats[event_name]['total_listeners'] += 1
        if module_name:
            self.listener_stats[event_name]['modules'].add(module_name)
    
    def unregister_listener(self, event_name: str, callback: Callable):
        """Desregistra un event listener"""
        if event_name in self.listeners:
            self.listeners[event_name] = [
                listener for listener in self.listeners[event_name] 
                if listener.callback != callback
            ]
            
            # Actualizar estadísticas
            if self.listeners[event_name]:
                self.listener_stats[event_name]['total_listeners'] = len(self.listeners[event_name])
            else:
                # Remover evento si no tiene listeners
                del self.listeners[event_name]
                del self.listener_stats[event_name]
    
    def notify_event(self, event_name: str, event_data: Dict) -> List[Dict]:
        """Notifica un evento a todos los listeners registrados"""
        results = []
        
        if event_name not in self.listeners:
            return results
        
        # Aplicar filtros si existen
        if event_name in self.event_filters:
            for filter_func in self.event_filters[event_name]:
                if not filter_func(event_data):
                    return results  # Evento filtrado
        
        # Ejecutar listeners
        for listener in self.listeners[event_name]:
            result = listener.execute(event_data)
            results.append({
                'listener': listener.get_stats(),
                'result': result
            })
            
            # Actualizar estadísticas
            self.listener_stats[event_name]['execution_count'] += 1
            if not result['success']:
                self.listener_stats[event_name]['error_count'] += 1
        
        return results
    
    def add_event_filter(self, event_name: str, filter_func: Callable):
        """Agrega un filtro para un evento específico"""
        if event_name not in self.event_filters:
            self.event_filters[event_name] = []
        
        self.event_filters[event_name].append(filter_func)
    
    def remove_event_filter(self, event_name: str, filter_func: Callable):
        """Remueve un filtro de evento"""
        if event_name in self.event_filters:
            self.event_filters[event_name] = [
                f for f in self.event_filters[event_name] 
                if f != filter_func
            ]
    
    def get_listener_stats(self, event_name: str = None) -> Dict:
        """Obtiene estadísticas de listeners"""
        if event_name:
            return self.listener_stats.get(event_name, {})
        
        return {
            'total_events': len(self.listeners),
            'total_listeners': sum(stats['total_listeners'] for stats in self.listener_stats.values()),
            'total_executions': sum(stats['execution_count'] for stats in self.listener_stats.values()),
            'total_errors': sum(stats['error_count'] for stats in self.listener_stats.values()),
            'events': list(self.listeners.keys()),
            'event_stats': self.listener_stats
        }
    
    def get_listener_details(self, event_name: str) -> List[Dict]:
        """Obtiene detalles de todos los listeners de un evento"""
        if event_name not in self.listeners:
            return []
        
        return [listener.get_stats() for listener in self.listeners[event_name]]
    
    def reload_listeners(self):
        """Recarga todos los listeners"""
        self.listeners = {}
        self.listener_stats = {}
        self.event_filters = {}
        self.load_listeners()
    
    def cleanup_module_listeners(self, module_name: str):
        """Limpia todos los listeners de un módulo específico"""
        for event_name in list(self.listeners.keys()):
            self.listeners[event_name] = [
                listener for listener in self.listeners[event_name] 
                if listener.module_name != module_name
            ]
            
            # Actualizar estadísticas
            if self.listeners[event_name]:
                self.listener_stats[event_name]['total_listeners'] = len(self.listeners[event_name])
            else:
                # Remover evento si no tiene listeners
                del self.listeners[event_name]
                del self.listener_stats[event_name]


# Instancia global del EventListenerManager
event_listener_manager = EventListenerManager() 