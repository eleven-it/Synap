"""
Gestor de extensiones del sistema Synap
Maneja extensiones que agregan funcionalidad a módulos existentes
"""

import os
import json
import importlib
import inspect
from typing import Dict, List, Any, Optional, Type
from django.conf import settings
from django.core.cache import cache
from core.plugin_manager import PluginBase


class ExtensionBase:
    """Clase base para todas las extensiones"""
    
    # Metadatos de la extensión
    name = None
    version = None
    description = None
    author = None
    target_module = None  # Módulo al que extiende
    
    # Configuración de la extensión
    extends_models = []      # Modelos que extiende
    extends_views = []       # Vistas que extiende
    extends_templates = []   # Templates que extiende
    extends_forms = []       # Formularios que extiende
    extends_admin = []       # Admin que extiende
    
    # Configuración por defecto
    default_config = {}
    
    def __init__(self):
        self.is_installed = False
        self.is_active = False
        self.config = self.default_config.copy()
    
    def install(self) -> bool:
        """
        Instala la extensión
        
        Returns:
            True si la instalación fue exitosa
        """
        try:
            # Verificar que el módulo objetivo existe
            if not self.check_target_module():
                return False
            
            # Ejecutar migraciones si existen
            self.run_migrations()
            
            # Extender modelos
            self.extend_models()
            
            # Extender vistas
            self.extend_views()
            
            # Extender templates
            self.extend_templates()
            
            # Extender formularios
            self.extend_forms()
            
            # Extender admin
            self.extend_admin()
            
            # Ejecutar código de instalación
            self.on_install()
            
            self.is_installed = True
            return True
            
        except Exception as e:
            print(f"Error installing extension {self.name}: {e}")
            return False
    
    def uninstall(self) -> bool:
        """
        Desinstala la extensión
        
        Returns:
            True si la desinstalación fue exitosa
        """
        try:
            # Ejecutar código de desinstalación
            self.on_uninstall()
            
            # Revertir extensiones
            self.revert_models()
            self.revert_views()
            self.revert_templates()
            self.revert_forms()
            self.revert_admin()
            
            # Ejecutar migraciones de desinstalación
            self.run_uninstall_migrations()
            
            self.is_installed = False
            return True
            
        except Exception as e:
            print(f"Error uninstalling extension {self.name}: {e}")
            return False
    
    def activate(self) -> bool:
        """
        Activa la extensión
        
        Returns:
            True si la activación fue exitosa
        """
        try:
            if not self.is_installed:
                if not self.install():
                    return False
            
            # Ejecutar código de activación
            self.on_activate()
            
            self.is_active = True
            return True
            
        except Exception as e:
            print(f"Error activating extension {self.name}: {e}")
            return False
    
    def deactivate(self) -> bool:
        """
        Desactiva la extensión
        
        Returns:
            True si la desactivación fue exitosa
        """
        try:
            # Ejecutar código de desactivación
            self.on_deactivate()
            
            self.is_active = False
            return True
            
        except Exception as e:
            print(f"Error deactivating extension {self.name}: {e}")
            return False
    
    def check_target_module(self) -> bool:
        """Verifica que el módulo objetivo existe y está activo"""
        if not self.target_module:
            return False
        
        from core.module_manager import module_manager
        return module_manager.is_module_active(self.target_module)
    
    def run_migrations(self):
        """Ejecuta migraciones de la extensión"""
        # Implementar en subclases si es necesario
        pass
    
    def run_uninstall_migrations(self):
        """Ejecuta migraciones de desinstalación"""
        # Implementar en subclases si es necesario
        pass
    
    def extend_models(self):
        """Extiende modelos del módulo objetivo"""
        # Implementar en subclases
        pass
    
    def extend_views(self):
        """Extiende vistas del módulo objetivo"""
        # Implementar en subclases
        pass
    
    def extend_templates(self):
        """Extiende templates del módulo objetivo"""
        # Implementar en subclases
        pass
    
    def extend_forms(self):
        """Extiende formularios del módulo objetivo"""
        # Implementar en subclases
        pass
    
    def extend_admin(self):
        """Extiende admin del módulo objetivo"""
        # Implementar en subclases
        pass
    
    def revert_models(self):
        """Revierte extensiones de modelos"""
        # Implementar en subclases
        pass
    
    def revert_views(self):
        """Revierte extensiones de vistas"""
        # Implementar en subclases
        pass
    
    def revert_templates(self):
        """Revierte extensiones de templates"""
        # Implementar en subclases
        pass
    
    def revert_forms(self):
        """Revierte extensiones de formularios"""
        # Implementar en subclases
        pass
    
    def revert_admin(self):
        """Revierte extensiones de admin"""
        # Implementar en subclases
        pass
    
    # Métodos que pueden ser sobrescritos por subclases
    def on_install(self):
        """Código que se ejecuta al instalar la extensión"""
        pass
    
    def on_uninstall(self):
        """Código que se ejecuta al desinstalar la extensión"""
        pass
    
    def on_activate(self):
        """Código que se ejecuta al activar la extensión"""
        pass
    
    def on_deactivate(self):
        """Código que se ejecuta al desactivar la extensión"""
        pass
    
    def get_config(self) -> Dict:
        """Obtiene la configuración de la extensión"""
        return self.config
    
    def set_config(self, config: Dict):
        """Establece la configuración de la extensión"""
        self.config.update(config)
    
    def get_info(self) -> Dict:
        """Obtiene información de la extensión"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'target_module': self.target_module,
            'is_installed': self.is_installed,
            'is_active': self.is_active,
            'extends_models': len(self.extends_models),
            'extends_views': len(self.extends_views),
            'extends_templates': len(self.extends_templates),
            'extends_forms': len(self.extends_forms),
            'extends_admin': len(self.extends_admin)
        }


class ExtensionManager:
    """Gestor principal de extensiones"""
    
    def __init__(self):
        self.extensions = {}
        self.extension_configs = {}
        self.extension_paths = []
        self.load_extension_paths()
        self.discover_extensions()
    
    def load_extension_paths(self):
        """Carga las rutas de extensiones desde la configuración"""
        # Ruta por defecto para extensiones
        default_extension_path = os.path.join(settings.BASE_DIR, 'extensions')
        if os.path.exists(default_extension_path):
            self.extension_paths.append(default_extension_path)
        
        # Rutas adicionales desde settings
        custom_extension_paths = getattr(settings, 'EXTENSION_PATHS', [])
        for path in custom_extension_paths:
            if os.path.exists(path):
                self.extension_paths.append(path)
    
    def discover_extensions(self):
        """Descubre extensiones disponibles"""
        for extension_path in self.extension_paths:
            if os.path.exists(extension_path):
                for item in os.listdir(extension_path):
                    extension_dir = os.path.join(extension_path, item)
                    if os.path.isdir(extension_dir):
                        self.load_extension_from_directory(extension_dir)
    
    def load_extension_from_directory(self, extension_dir: str):
        """Carga una extensión desde un directorio"""
        try:
            # Buscar archivo de configuración
            config_file = os.path.join(extension_dir, 'extension.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Buscar archivo principal de la extensión
                main_file = os.path.join(extension_dir, 'extension.py')
                if os.path.exists(main_file):
                    self.load_extension_from_file(main_file, config)
                    
        except Exception as e:
            print(f"Error loading extension from {extension_dir}: {e}")
    
    def load_extension_from_file(self, extension_file: str, config: Dict):
        """Carga una extensión desde un archivo"""
        try:
            # Importar el módulo de la extensión
            module_name = os.path.basename(extension_file).replace('.py', '')
            spec = importlib.util.spec_from_file_location(module_name, extension_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Buscar la clase de la extensión
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, ExtensionBase) and 
                    obj != ExtensionBase):
                    
                    # Crear instancia de la extensión
                    extension = obj()
                    
                    # Aplicar configuración
                    if config:
                        extension.set_config(config)
                    
                    # Registrar la extensión
                    self.register_extension(extension)
                    break
                    
        except Exception as e:
            print(f"Error loading extension from {extension_file}: {e}")
    
    def register_extension(self, extension: ExtensionBase):
        """Registra una extensión"""
        if extension.name:
            self.extensions[extension.name] = extension
            print(f"Extension {extension.name} registered")
    
    def get_extension(self, extension_name: str) -> Optional[ExtensionBase]:
        """Obtiene una extensión por nombre"""
        return self.extensions.get(extension_name)
    
    def get_all_extensions(self) -> Dict[str, ExtensionBase]:
        """Obtiene todas las extensiones registradas"""
        return self.extensions.copy()
    
    def get_extensions_by_module(self, module_name: str) -> List[ExtensionBase]:
        """Obtiene extensiones por módulo objetivo"""
        return [
            extension for extension in self.extensions.values()
            if extension.target_module == module_name
        ]
    
    def get_installed_extensions(self) -> List[ExtensionBase]:
        """Obtiene extensiones instaladas"""
        return [extension for extension in self.extensions.values() if extension.is_installed]
    
    def get_active_extensions(self) -> List[ExtensionBase]:
        """Obtiene extensiones activas"""
        return [extension for extension in self.extensions.values() if extension.is_active]
    
    def install_extension(self, extension_name: str) -> bool:
        """Instala una extensión"""
        extension = self.get_extension(extension_name)
        if not extension:
            print(f"Extension {extension_name} not found")
            return False
        
        return extension.install()
    
    def uninstall_extension(self, extension_name: str) -> bool:
        """Desinstala una extensión"""
        extension = self.get_extension(extension_name)
        if not extension:
            print(f"Extension {extension_name} not found")
            return False
        
        return extension.uninstall()
    
    def activate_extension(self, extension_name: str) -> bool:
        """Activa una extensión"""
        extension = self.get_extension(extension_name)
        if not extension:
            print(f"Extension {extension_name} not found")
            return False
        
        return extension.activate()
    
    def deactivate_extension(self, extension_name: str) -> bool:
        """Desactiva una extensión"""
        extension = self.get_extension(extension_name)
        if not extension:
            print(f"Extension {extension_name} not found")
            return False
        
        return extension.deactivate()
    
    def get_extension_info(self, extension_name: str) -> Dict:
        """Obtiene información de una extensión"""
        extension = self.get_extension(extension_name)
        if not extension:
            return {}
        
        return extension.get_info()
    
    def get_extensions_summary(self) -> Dict:
        """Obtiene resumen de todas las extensiones"""
        total_extensions = len(self.extensions)
        installed_extensions = len(self.get_installed_extensions())
        active_extensions = len(self.get_active_extensions())
        
        extensions_info = []
        for extension in self.extensions.values():
            extensions_info.append(extension.get_info())
        
        # Agrupar por módulo objetivo
        by_module = {}
        for extension in self.extensions.values():
            module = extension.target_module or 'general'
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(extension.get_info())
        
        return {
            'total_extensions': total_extensions,
            'installed_extensions': installed_extensions,
            'active_extensions': active_extensions,
            'extensions': extensions_info,
            'by_module': by_module
        }
    
    def validate_extension(self, extension_name: str) -> Dict:
        """Valida una extensión"""
        extension = self.get_extension(extension_name)
        if not extension:
            return {'valid': False, 'error': 'Extension not found'}
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Verificar módulo objetivo
        if not extension.check_target_module():
            validation_results['valid'] = False
            validation_results['errors'].append('Target module not active')
        
        # Verificar metadatos
        if not extension.name:
            validation_results['warnings'].append('Extension name not set')
        
        if not extension.version:
            validation_results['warnings'].append('Extension version not set')
        
        if not extension.target_module:
            validation_results['warnings'].append('Target module not specified')
        
        return validation_results
    
    def reload_extensions(self):
        """Recarga todas las extensiones"""
        self.extensions = {}
        self.discover_extensions()
    
    def cleanup_extension(self, extension_name: str):
        """Limpia una extensión del sistema"""
        extension = self.get_extension(extension_name)
        if extension:
            if extension.is_active:
                extension.deactivate()
            if extension.is_installed:
                extension.uninstall()
            
            del self.extensions[extension_name]


# Instancia global del ExtensionManager
extension_manager = ExtensionManager() 