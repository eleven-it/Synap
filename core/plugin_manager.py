"""
Gestor de plugins y extensiones del sistema Synap
Maneja la instalación, activación y gestión de plugins modulares
"""

import os
import json
import importlib
import inspect
from typing import Dict, List, Any, Optional, Type
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from core.module_manager import module_manager
from core.hook_manager import hook_manager
from core.event_dispatcher import event_dispatcher


class PluginBase:
    """Clase base para todos los plugins"""
    
    # Metadatos del plugin
    name = None
    version = None
    description = None
    author = None
    website = None
    license = None
    
    # Configuración del plugin
    requires_modules = []  # Módulos requeridos
    optional_modules = []  # Módulos opcionales
    conflicts_with = []    # Plugins con los que puede conflictuar
    
    # Hooks que el plugin registra
    hooks = {}
    
    # Eventos que el plugin escucha
    events = {}
    
    # URLs que el plugin agrega
    urls = []
    
    # Templates que el plugin proporciona
    templates = []
    
    # Configuración por defecto
    default_config = {}
    
    def __init__(self):
        self.is_installed = False
        self.is_active = False
        self.config = self.default_config.copy()
    
    def install(self) -> bool:
        """
        Instala el plugin
        
        Returns:
            True si la instalación fue exitosa
        """
        try:
            # Verificar dependencias
            if not self.check_dependencies():
                return False
            
            # Ejecutar migraciones si existen
            self.run_migrations()
            
            # Crear tablas si es necesario
            self.create_tables()
            
            # Registrar hooks
            self.register_hooks()
            
            # Registrar eventos
            self.register_events()
            
            # Ejecutar código de instalación
            self.on_install()
            
            self.is_installed = True
            return True
            
        except Exception as e:
            print(f"Error installing plugin {self.name}: {e}")
            return False
    
    def uninstall(self) -> bool:
        """
        Desinstala el plugin
        
        Returns:
            True si la desinstalación fue exitosa
        """
        try:
            # Ejecutar código de desinstalación
            self.on_uninstall()
            
            # Desregistrar eventos
            self.unregister_events()
            
            # Desregistrar hooks
            self.unregister_hooks()
            
            # Eliminar tablas si es necesario
            self.drop_tables()
            
            # Ejecutar migraciones de desinstalación
            self.run_uninstall_migrations()
            
            self.is_installed = False
            return True
            
        except Exception as e:
            print(f"Error uninstalling plugin {self.name}: {e}")
            return False
    
    def activate(self) -> bool:
        """
        Activa el plugin
        
        Returns:
            True si la activación fue exitosa
        """
        try:
            if not self.is_installed:
                if not self.install():
                    return False
            
            # Verificar conflictos
            if not self.check_conflicts():
                return False
            
            # Ejecutar código de activación
            self.on_activate()
            
            self.is_active = True
            return True
            
        except Exception as e:
            print(f"Error activating plugin {self.name}: {e}")
            return False
    
    def deactivate(self) -> bool:
        """
        Desactiva el plugin
        
        Returns:
            True si la desactivación fue exitosa
        """
        try:
            # Ejecutar código de desactivación
            self.on_deactivate()
            
            self.is_active = False
            return True
            
        except Exception as e:
            print(f"Error deactivating plugin {self.name}: {e}")
            return False
    
    def check_dependencies(self) -> bool:
        """Verifica que las dependencias estén satisfechas"""
        # Verificar módulos requeridos
        for module in self.requires_modules:
            if not module_manager.is_module_active(module):
                print(f"Required module {module} is not active")
                return False
        
        return True
    
    def check_conflicts(self) -> bool:
        """Verifica conflictos con otros plugins"""
        from core.plugin_registry import plugin_registry
        
        for conflicting_plugin in self.conflicts_with:
            if plugin_registry.is_plugin_active(conflicting_plugin):
                print(f"Plugin conflicts with {conflicting_plugin}")
                return False
        
        return True
    
    def run_migrations(self):
        """Ejecuta migraciones del plugin"""
        # Implementar en subclases si es necesario
        pass
    
    def create_tables(self):
        """Crea tablas necesarias para el plugin"""
        # Implementar en subclases si es necesario
        pass
    
    def drop_tables(self):
        """Elimina tablas del plugin"""
        # Implementar en subclases si es necesario
        pass
    
    def run_uninstall_migrations(self):
        """Ejecuta migraciones de desinstalación"""
        # Implementar en subclases si es necesario
        pass
    
    def register_hooks(self):
        """Registra hooks del plugin"""
        for hook_name, callback in self.hooks.items():
            hook_manager.register_hook(hook_name, callback, self.name)
    
    def unregister_hooks(self):
        """Desregistra hooks del plugin"""
        for hook_name, callback in self.hooks.items():
            hook_manager.unregister_hook(hook_name, callback)
    
    def register_events(self):
        """Registra eventos del plugin"""
        for event_name, callback in self.events.items():
            event_dispatcher.register_event_listener(event_name, callback, self.name)
    
    def unregister_events(self):
        """Desregistra eventos del plugin"""
        for event_name, callback in self.events.items():
            event_dispatcher.unregister_event_listener(event_name, callback)
    
    # Métodos que pueden ser sobrescritos por subclases
    def on_install(self):
        """Código que se ejecuta al instalar el plugin"""
        pass
    
    def on_uninstall(self):
        """Código que se ejecuta al desinstalar el plugin"""
        pass
    
    def on_activate(self):
        """Código que se ejecuta al activar el plugin"""
        pass
    
    def on_deactivate(self):
        """Código que se ejecuta al desactivar el plugin"""
        pass
    
    def get_config(self) -> Dict:
        """Obtiene la configuración del plugin"""
        return self.config
    
    def set_config(self, config: Dict):
        """Establece la configuración del plugin"""
        self.config.update(config)
    
    def get_info(self) -> Dict:
        """Obtiene información del plugin"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'website': self.website,
            'license': self.license,
            'requires_modules': self.requires_modules,
            'optional_modules': self.optional_modules,
            'conflicts_with': self.conflicts_with,
            'is_installed': self.is_installed,
            'is_active': self.is_active,
            'hooks_count': len(self.hooks),
            'events_count': len(self.events),
            'urls_count': len(self.urls),
            'templates_count': len(self.templates)
        }


class PluginManager:
    """Gestor principal de plugins"""
    
    def __init__(self):
        self.plugins = {}
        self.plugin_configs = {}
        self.plugin_paths = []
        self.load_plugin_paths()
        self.discover_plugins()
    
    def load_plugin_paths(self):
        """Carga las rutas de plugins desde la configuración"""
        # Ruta por defecto para plugins
        default_plugin_path = os.path.join(settings.BASE_DIR, 'plugins')
        if os.path.exists(default_plugin_path):
            self.plugin_paths.append(default_plugin_path)
        
        # Rutas adicionales desde settings
        custom_plugin_paths = getattr(settings, 'PLUGIN_PATHS', [])
        for path in custom_plugin_paths:
            if os.path.exists(path):
                self.plugin_paths.append(path)
    
    def discover_plugins(self):
        """Descubre plugins disponibles"""
        for plugin_path in self.plugin_paths:
            if os.path.exists(plugin_path):
                for item in os.listdir(plugin_path):
                    plugin_dir = os.path.join(plugin_path, item)
                    if os.path.isdir(plugin_dir):
                        self.load_plugin_from_directory(plugin_dir)
    
    def load_plugin_from_directory(self, plugin_dir: str):
        """Carga un plugin desde un directorio"""
        try:
            # Buscar archivo de configuración
            config_file = os.path.join(plugin_dir, 'plugin.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Buscar archivo principal del plugin
                main_file = os.path.join(plugin_dir, 'plugin.py')
                if os.path.exists(main_file):
                    self.load_plugin_from_file(main_file, config)
                    
        except Exception as e:
            print(f"Error loading plugin from {plugin_dir}: {e}")
    
    def load_plugin_from_file(self, plugin_file: str, config: Dict):
        """Carga un plugin desde un archivo"""
        try:
            # Importar el módulo del plugin
            module_name = os.path.basename(plugin_file).replace('.py', '')
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Buscar la clase del plugin
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj != PluginBase):
                    
                    # Crear instancia del plugin
                    plugin = obj()
                    
                    # Aplicar configuración
                    if config:
                        plugin.set_config(config)
                    
                    # Registrar el plugin
                    self.register_plugin(plugin)
                    break
                    
        except Exception as e:
            print(f"Error loading plugin from {plugin_file}: {e}")
    
    def register_plugin(self, plugin: PluginBase):
        """Registra un plugin"""
        if plugin.name:
            self.plugins[plugin.name] = plugin
            print(f"Plugin {plugin.name} registered")
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Obtiene un plugin por nombre"""
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginBase]:
        """Obtiene todos los plugins registrados"""
        return self.plugins.copy()
    
    def get_installed_plugins(self) -> List[PluginBase]:
        """Obtiene plugins instalados"""
        return [plugin for plugin in self.plugins.values() if plugin.is_installed]
    
    def get_active_plugins(self) -> List[PluginBase]:
        """Obtiene plugins activos"""
        return [plugin for plugin in self.plugins.values() if plugin.is_active]
    
    def install_plugin(self, plugin_name: str) -> bool:
        """Instala un plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"Plugin {plugin_name} not found")
            return False
        
        return plugin.install()
    
    def uninstall_plugin(self, plugin_name: str) -> bool:
        """Desinstala un plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"Plugin {plugin_name} not found")
            return False
        
        return plugin.uninstall()
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """Activa un plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"Plugin {plugin_name} not found")
            return False
        
        return plugin.activate()
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """Desactiva un plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            print(f"Plugin {plugin_name} not found")
            return False
        
        return plugin.deactivate()
    
    def get_plugin_info(self, plugin_name: str) -> Dict:
        """Obtiene información de un plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {}
        
        return plugin.get_info()
    
    def get_plugins_summary(self) -> Dict:
        """Obtiene resumen de todos los plugins"""
        total_plugins = len(self.plugins)
        installed_plugins = len(self.get_installed_plugins())
        active_plugins = len(self.get_active_plugins())
        
        plugins_info = []
        for plugin in self.plugins.values():
            plugins_info.append(plugin.get_info())
        
        return {
            'total_plugins': total_plugins,
            'installed_plugins': installed_plugins,
            'active_plugins': active_plugins,
            'plugins': plugins_info
        }
    
    def validate_plugin(self, plugin_name: str) -> Dict:
        """Valida un plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {'valid': False, 'error': 'Plugin not found'}
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Verificar dependencias
        if not plugin.check_dependencies():
            validation_results['valid'] = False
            validation_results['errors'].append('Dependencies not satisfied')
        
        # Verificar conflictos
        if not plugin.check_conflicts():
            validation_results['valid'] = False
            validation_results['errors'].append('Conflicts detected')
        
        # Verificar metadatos
        if not plugin.name:
            validation_results['warnings'].append('Plugin name not set')
        
        if not plugin.version:
            validation_results['warnings'].append('Plugin version not set')
        
        return validation_results
    
    def reload_plugins(self):
        """Recarga todos los plugins"""
        self.plugins = {}
        self.discover_plugins()
    
    def cleanup_plugin(self, plugin_name: str):
        """Limpia un plugin del sistema"""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            if plugin.is_active:
                plugin.deactivate()
            if plugin.is_installed:
                plugin.uninstall()
            
            del self.plugins[plugin_name]


# Instancia global del PluginManager
plugin_manager = PluginManager() 