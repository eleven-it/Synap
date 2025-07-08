"""
Registro de plugins del sistema Synap
Gestiona el registro y descubrimiento de plugins de manera centralizada
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional
from django.core.cache import cache
from django.conf import settings
from core.plugin_manager import plugin_manager, PluginBase


class PluginRegistry:
    """Registro centralizado de plugins del sistema"""
    
    def __init__(self):
        self.registered_plugins = {}
        self.plugin_metadata = {}
        self.plugin_dependencies = {}
        self.plugin_conflicts = {}
        self.plugin_categories = {}
        self.load_registry()
    
    def load_registry(self):
        """Carga el registro de plugins desde archivos de configuración"""
        # Cargar desde archivo de registro principal
        registry_file = os.path.join(settings.BASE_DIR, 'core', 'data', 'plugin_registry.json')
        if os.path.exists(registry_file):
            try:
                with open(registry_file, 'r') as f:
                    registry_data = json.load(f)
                    self.registered_plugins = registry_data.get('plugins', {})
                    self.plugin_metadata = registry_data.get('metadata', {})
                    self.plugin_dependencies = registry_data.get('dependencies', {})
                    self.plugin_conflicts = registry_data.get('conflicts', {})
                    self.plugin_categories = registry_data.get('categories', {})
            except Exception as e:
                print(f"Error loading plugin registry: {e}")
        
        # Cargar plugins descubiertos por el PluginManager
        discovered_plugins = plugin_manager.get_all_plugins()
        for plugin_name, plugin in discovered_plugins.items():
            if plugin_name not in self.registered_plugins:
                self.register_plugin(plugin_name, plugin)
    
    def register_plugin(self, plugin_name: str, plugin: PluginBase):
        """Registra un plugin en el registro"""
        plugin_info = plugin.get_info()
        
        self.registered_plugins[plugin_name] = {
            'name': plugin_name,
            'class': plugin.__class__.__name__,
            'module': plugin.__class__.__module__,
            'version': plugin_info.get('version'),
            'description': plugin_info.get('description'),
            'author': plugin_info.get('author'),
            'website': plugin_info.get('website'),
            'license': plugin_info.get('license'),
            'category': self.get_plugin_category(plugin_name),
            'is_installed': plugin_info.get('is_installed', False),
            'is_active': plugin_info.get('is_active', False),
            'hooks_count': plugin_info.get('hooks_count', 0),
            'events_count': plugin_info.get('events_count', 0),
            'urls_count': plugin_info.get('urls_count', 0),
            'templates_count': plugin_info.get('templates_count', 0)
        }
        
        # Registrar metadatos
        self.plugin_metadata[plugin_name] = {
            'requires_modules': plugin_info.get('requires_modules', []),
            'optional_modules': plugin_info.get('optional_modules', []),
            'conflicts_with': plugin_info.get('conflicts_with', []),
            'tags': self.get_plugin_tags(plugin_name),
            'compatibility': self.get_plugin_compatibility(plugin_name)
        }
        
        # Registrar dependencias
        self.plugin_dependencies[plugin_name] = {
            'required': plugin_info.get('requires_modules', []),
            'optional': plugin_info.get('optional_modules', []),
            'provides': self.get_plugin_provides(plugin_name)
        }
        
        # Registrar conflictos
        self.plugin_conflicts[plugin_name] = plugin_info.get('conflicts_with', [])
    
    def get_plugin_category(self, plugin_name: str) -> str:
        """Obtiene la categoría de un plugin"""
        # Intentar obtener desde el registro
        if plugin_name in self.plugin_categories:
            return self.plugin_categories[plugin_name]
        
        # Categorías por defecto basadas en el nombre
        if 'report' in plugin_name.lower():
            return 'reports'
        elif 'integration' in plugin_name.lower():
            return 'integrations'
        elif 'theme' in plugin_name.lower():
            return 'themes'
        elif 'payment' in plugin_name.lower():
            return 'payments'
        elif 'shipping' in plugin_name.lower():
            return 'shipping'
        else:
            return 'general'
    
    def get_plugin_tags(self, plugin_name: str) -> List[str]:
        """Obtiene las etiquetas de un plugin"""
        # Implementar lógica para obtener etiquetas
        return []
    
    def get_plugin_compatibility(self, plugin_name: str) -> Dict:
        """Obtiene la compatibilidad de un plugin"""
        return {
            'synap_version': '1.0.0',
            'python_version': '3.8+',
            'django_version': '4.0+'
        }
    
    def get_plugin_provides(self, plugin_name: str) -> List[str]:
        """Obtiene lo que proporciona un plugin"""
        # Implementar lógica para obtener funcionalidades proporcionadas
        return []
    
    def get_plugin_info(self, plugin_name: str) -> Dict:
        """Obtiene información detallada de un plugin"""
        if plugin_name not in self.registered_plugins:
            return {}
        
        plugin_data = self.registered_plugins[plugin_name]
        metadata = self.plugin_metadata.get(plugin_name, {})
        dependencies = self.plugin_dependencies.get(plugin_name, {})
        conflicts = self.plugin_conflicts.get(plugin_name, [])
        
        return {
            **plugin_data,
            'metadata': metadata,
            'dependencies': dependencies,
            'conflicts': conflicts,
            'can_install': self.can_install_plugin(plugin_name),
            'can_activate': self.can_activate_plugin(plugin_name),
            'validation': self.validate_plugin(plugin_name)
        }
    
    def get_all_plugins(self) -> Dict:
        """Obtiene información de todos los plugins registrados"""
        return {
            plugin_name: self.get_plugin_info(plugin_name)
            for plugin_name in self.registered_plugins.keys()
        }
    
    def get_plugins_by_category(self, category: str) -> List[Dict]:
        """Obtiene plugins por categoría"""
        plugins = []
        for plugin_name, plugin_info in self.registered_plugins.items():
            if plugin_info.get('category') == category:
                plugins.append(self.get_plugin_info(plugin_name))
        return plugins
    
    def get_installed_plugins(self) -> List[Dict]:
        """Obtiene plugins instalados"""
        plugins = []
        for plugin_name, plugin_info in self.registered_plugins.items():
            if plugin_info.get('is_installed'):
                plugins.append(self.get_plugin_info(plugin_name))
        return plugins
    
    def get_active_plugins(self) -> List[Dict]:
        """Obtiene plugins activos"""
        plugins = []
        for plugin_name, plugin_info in self.registered_plugins.items():
            if plugin_info.get('is_active'):
                plugins.append(self.get_plugin_info(plugin_name))
        return plugins
    
    def can_install_plugin(self, plugin_name: str) -> bool:
        """Verifica si un plugin puede ser instalado"""
        if plugin_name not in self.registered_plugins:
            return False
        
        # Verificar dependencias
        dependencies = self.plugin_dependencies.get(plugin_name, {})
        required_modules = dependencies.get('required', [])
        
        from core.module_manager import module_manager
        for module in required_modules:
            if not module_manager.is_module_active(module):
                return False
        
        return True
    
    def can_activate_plugin(self, plugin_name: str) -> bool:
        """Verifica si un plugin puede ser activado"""
        if not self.can_install_plugin(plugin_name):
            return False
        
        # Verificar conflictos
        conflicts = self.plugin_conflicts.get(plugin_name, [])
        for conflicting_plugin in conflicts:
            if self.is_plugin_active(conflicting_plugin):
                return False
        
        return True
    
    def is_plugin_installed(self, plugin_name: str) -> bool:
        """Verifica si un plugin está instalado"""
        return self.registered_plugins.get(plugin_name, {}).get('is_installed', False)
    
    def is_plugin_active(self, plugin_name: str) -> bool:
        """Verifica si un plugin está activo"""
        return self.registered_plugins.get(plugin_name, {}).get('is_active', False)
    
    def validate_plugin(self, plugin_name: str) -> Dict:
        """Valida un plugin"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if plugin_name not in self.registered_plugins:
            validation_results['valid'] = False
            validation_results['errors'].append('Plugin not found in registry')
            return validation_results
        
        plugin_info = self.registered_plugins[plugin_name]
        
        # Verificar metadatos requeridos
        if not plugin_info.get('name'):
            validation_results['warnings'].append('Plugin name not set')
        
        if not plugin_info.get('version'):
            validation_results['warnings'].append('Plugin version not set')
        
        if not plugin_info.get('description'):
            validation_results['warnings'].append('Plugin description not set')
        
        # Verificar dependencias
        dependencies = self.plugin_dependencies.get(plugin_name, {})
        required_modules = dependencies.get('required', [])
        
        from core.module_manager import module_manager
        for module in required_modules:
            if not module_manager.is_module_active(module):
                validation_results['errors'].append(f'Required module {module} is not active')
                validation_results['valid'] = False
        
        # Verificar conflictos
        conflicts = self.plugin_conflicts.get(plugin_name, [])
        for conflicting_plugin in conflicts:
            if self.is_plugin_active(conflicting_plugin):
                validation_results['errors'].append(f'Conflicts with active plugin {conflicting_plugin}')
                validation_results['valid'] = False
        
        return validation_results
    
    def get_plugin_statistics(self) -> Dict:
        """Obtiene estadísticas del registro de plugins"""
        total_plugins = len(self.registered_plugins)
        installed_plugins = len(self.get_installed_plugins())
        active_plugins = len(self.get_active_plugins())
        
        # Contar por categoría
        category_counts = {}
        for plugin_info in self.registered_plugins.values():
            category = plugin_info.get('category', 'general')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Contar por estado
        status_counts = {
            'installed': installed_plugins,
            'active': active_plugins,
            'inactive': total_plugins - installed_plugins
        }
        
        return {
            'total_plugins': total_plugins,
            'installed_plugins': installed_plugins,
            'active_plugins': active_plugins,
            'category_counts': category_counts,
            'status_counts': status_counts
        }
    
    def get_plugin_dependencies_graph(self) -> Dict:
        """Obtiene grafo de dependencias de plugins"""
        graph = {}
        
        for plugin_name, dependencies in self.plugin_dependencies.items():
            graph[plugin_name] = {
                'required': dependencies.get('required', []),
                'optional': dependencies.get('optional', []),
                'provides': dependencies.get('provides', []),
                'conflicts': self.plugin_conflicts.get(plugin_name, [])
            }
        
        return graph
    
    def find_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """Encuentra plugins que dependen de uno específico"""
        dependent_plugins = []
        
        for p_name, dependencies in self.plugin_dependencies.items():
            if plugin_name in dependencies.get('required', []):
                dependent_plugins.append(p_name)
        
        return dependent_plugins
    
    def find_plugin_conflicts(self, plugin_name: str) -> List[str]:
        """Encuentra plugins que conflictúan con uno específico"""
        return self.plugin_conflicts.get(plugin_name, [])
    
    def update_plugin_status(self, plugin_name: str, is_installed: bool = None, is_active: bool = None):
        """Actualiza el estado de un plugin"""
        if plugin_name in self.registered_plugins:
            if is_installed is not None:
                self.registered_plugins[plugin_name]['is_installed'] = is_installed
            
            if is_active is not None:
                self.registered_plugins[plugin_name]['is_active'] = is_active
    
    def save_registry(self):
        """Guarda el registro en archivo"""
        registry_data = {
            'plugins': self.registered_plugins,
            'metadata': self.plugin_metadata,
            'dependencies': self.plugin_dependencies,
            'conflicts': self.plugin_conflicts,
            'categories': self.plugin_categories
        }
        
        registry_file = os.path.join(settings.BASE_DIR, 'core', 'data', 'plugin_registry.json')
        os.makedirs(os.path.dirname(registry_file), exist_ok=True)
        
        with open(registry_file, 'w') as f:
            json.dump(registry_data, f, indent=2)
    
    def reload_registry(self):
        """Recarga el registro completo"""
        self.registered_plugins = {}
        self.plugin_metadata = {}
        self.plugin_dependencies = {}
        self.plugin_conflicts = {}
        self.plugin_categories = {}
        self.load_registry()
    
    def cleanup_plugin(self, plugin_name: str):
        """Limpia un plugin del registro"""
        if plugin_name in self.registered_plugins:
            del self.registered_plugins[plugin_name]
        
        if plugin_name in self.plugin_metadata:
            del self.plugin_metadata[plugin_name]
        
        if plugin_name in self.plugin_dependencies:
            del self.plugin_dependencies[plugin_name]
        
        if plugin_name in self.plugin_conflicts:
            del self.plugin_conflicts[plugin_name]


# Instancia global del PluginRegistry
plugin_registry = PluginRegistry() 