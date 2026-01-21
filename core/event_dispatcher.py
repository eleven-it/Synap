"""
Dispatcher de eventos del sistema Synap
Maneja eventos de manera asíncrona y distribuida
"""

import asyncio
import threading
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from django.core.cache import cache
from django.db import transaction
from core.hook_manager import hook_manager


class EventDispatcher:
    """Dispatcher de eventos del sistema"""
    
    def __init__(self):
        self.event_queue = []
        self.event_history = []
        self.max_history = 1000
        self.is_running = False
        self.event_thread = None
        self.event_handlers = {}
        self.event_filters = {}
        self.load_event_handlers()
    
    def load_event_handlers(self):
        """Carga los manejadores de eventos de todos los módulos activos"""
        from core.module_manager import module_manager
        
        for module_name in module_manager.get_active_modules():
            try:
                handlers = self.get_module_event_handlers(module_name)
                if handlers:
                    self.event_handlers[module_name] = handlers
            except ImportError:
                # Módulo no tiene configuración de event handlers
                pass
            except Exception as e:
                print(f"Error loading event handlers for module {module_name}: {e}")
    
    def get_module_event_handlers(self, module_name):
        """Obtiene los manejadores de eventos de un módulo"""
        try:
            module = __import__(f'{module_name}.events', fromlist=['EVENT_HANDLERS'])
            return getattr(module, 'EVENT_HANDLERS', {})
        except ImportError:
            # Módulo no tiene archivo events.py
            return {}
        except AttributeError:
            # Módulo no tiene EVENT_HANDLERS definido
            return {}
    
    def dispatch_event(self, event_name: str, data: Any = None, source_module: str = None, 
                      priority: str = 'normal', async_execution: bool = True):
        """
        Dispara un evento
        
        Args:
            event_name: Nombre del evento
            data: Datos del evento
            source_module: Módulo que dispara el evento
            priority: Prioridad del evento (low, normal, high, critical)
            async_execution: Si debe ejecutarse de forma asíncrona
        """
        event = {
            'name': event_name,
            'data': data,
            'source_module': source_module,
            'priority': priority,
            'timestamp': datetime.now(),
            'id': f"{event_name}_{datetime.now().timestamp()}"
        }
        
        # Agregar a la cola de eventos
        self.event_queue.append(event)
        
        # Agregar al historial
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Ejecutar inmediatamente si no es asíncrono
        if not async_execution:
            self.process_event(event)
        else:
            # Iniciar el procesamiento asíncrono si no está corriendo
            if not self.is_running:
                self.start_event_processing()
    
    def process_event(self, event: Dict):
        """Procesa un evento específico"""
        event_name = event['name']
        
        # Ejecutar hooks relacionados con el evento
        hook_results = hook_manager.execute_hook(f"event_{event_name}", event)
        
        # Ejecutar manejadores de eventos específicos
        handler_results = self.execute_event_handlers(event)
        
        # Emitir evento a través del hook manager
        hook_manager.emit_event(event_name, event)
        
        return {
            'event_id': event['id'],
            'hook_results': hook_results,
            'handler_results': handler_results
        }
    
    def execute_event_handlers(self, event: Dict) -> List[Dict]:
        """Ejecuta los manejadores de eventos específicos"""
        results = []
        event_name = event['name']
        
        for module_name, handlers in self.event_handlers.items():
            if event_name in handlers:
                handler = handlers[event_name]
                try:
                    result = handler(event)
                    results.append({
                        'module': module_name,
                        'handler': handler.__name__,
                        'result': result,
                        'success': True
                    })
                except Exception as e:
                    results.append({
                        'module': module_name,
                        'handler': handler.__name__,
                        'error': str(e),
                        'success': False
                    })
        
        return results
    
    def start_event_processing(self):
        """Inicia el procesamiento asíncrono de eventos"""
        if self.is_running:
            return
        
        self.is_running = True
        self.event_thread = threading.Thread(target=self._event_processing_loop)
        self.event_thread.daemon = True
        self.event_thread.start()
    
    def stop_event_processing(self):
        """Detiene el procesamiento de eventos"""
        self.is_running = False
        if self.event_thread:
            self.event_thread.join()
    
    def _event_processing_loop(self):
        """Loop principal de procesamiento de eventos"""
        while self.is_running:
            if self.event_queue:
                # Procesar eventos por prioridad
                self._sort_events_by_priority()
                
                event = self.event_queue.pop(0)
                try:
                    self.process_event(event)
                except Exception as e:
                    print(f"Error processing event {event['name']}: {e}")
            
            # Pequeña pausa para no saturar la CPU
            import time
            time.sleep(0.1)
    
    def _sort_events_by_priority(self):
        """Ordena los eventos por prioridad"""
        priority_order = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}
        self.event_queue.sort(key=lambda x: priority_order.get(x['priority'], 2))
    
    def register_event_handler(self, event_name: str, handler: Callable, module_name: str = None):
        """Registra un manejador de eventos específico"""
        if module_name not in self.event_handlers:
            self.event_handlers[module_name] = {}
        
        self.event_handlers[module_name][event_name] = handler
    
    def unregister_event_handler(self, event_name: str, module_name: str):
        """Desregistra un manejador de eventos"""
        if module_name in self.event_handlers and event_name in self.event_handlers[module_name]:
            del self.event_handlers[module_name][event_name]
    
    def get_event_statistics(self) -> Dict:
        """Obtiene estadísticas de eventos"""
        event_counts = {}
        for event in self.event_history:
            event_name = event['name']
            event_counts[event_name] = event_counts.get(event_name, 0) + 1
        
        return {
            'total_events': len(self.event_history),
            'queued_events': len(self.event_queue),
            'event_counts': event_counts,
            'is_processing': self.is_running
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Obtiene eventos recientes"""
        return self.event_history[-limit:]
    
    def clear_event_history(self):
        """Limpia el historial de eventos"""
        self.event_history.clear()
    
    def add_event_filter(self, filter_name: str, filter_func: Callable):
        """Agrega un filtro de eventos"""
        self.event_filters[filter_name] = filter_func
    
    def apply_event_filters(self, event: Dict) -> bool:
        """Aplica filtros a un evento"""
        for filter_name, filter_func in self.event_filters.items():
            try:
                if not filter_func(event):
                    return False
            except Exception as e:
                print(f"Error applying filter {filter_name}: {e}")
                return False
        return True
    
    def reload_event_handlers(self):
        """Recarga los manejadores de eventos"""
        self.event_handlers = {}
        self.load_event_handlers()


# Instancia global del EventDispatcher
event_dispatcher = EventDispatcher() 