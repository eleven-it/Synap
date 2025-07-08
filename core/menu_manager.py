"""
Gestor de menús dinámicos por módulo
Maneja la carga y filtrado de menús según módulos activos y permisos del usuario
"""

from django.core.cache import cache
from core.module_manager import module_manager


class MenuManager:
    """Gestor de menús dinámicos por módulo"""
    
    def __init__(self):
        self.module_menus = {}
        self.load_module_menus()
    
    def load_module_menus(self):
        """Carga los menús de los módulos activos"""
        for module_name in module_manager.get_active_modules():
            try:
                menu_config = self.get_module_menu(module_name)
                if menu_config:
                    self.module_menus[module_name] = menu_config
            except ImportError:
                # Módulo no tiene configuración de menú
                pass
            except Exception as e:
                print(f"Error loading menu for module {module_name}: {e}")
    
    def get_module_menu(self, module_name):
        """Obtiene la configuración de menú de un módulo"""
        try:
            module = __import__(f'{module_name}.menu_config', fromlist=['MENU_CONFIG'])
            return getattr(module, 'MENU_CONFIG', [])
        except ImportError:
            # Módulo no tiene archivo menu_config.py
            return []
        except AttributeError:
            # Módulo no tiene MENU_CONFIG definido
            return []
    
    def get_user_menu(self, user):
        """Obtiene el menú completo para un usuario"""
        cache_key = f'user_menu_{user.id}_{user.fecha_modificacion.timestamp()}'
        menu = cache.get(cache_key)
        
        if menu is None:
            menu = []
            
            # Menú base (siempre disponible)
            menu.extend(self.get_base_menu(user))
            
            # Menús de módulos activos
            for module_name, menu_config in self.module_menus.items():
                if self.user_has_module_access(user, module_name):
                    filtered_menu = self.filter_menu_by_permissions(menu_config, user)
                    if filtered_menu:
                        menu.extend(filtered_menu)
            
            # Cache por 5 minutos
            cache.set(cache_key, menu, 300)
        
        return menu
    
    def get_base_menu(self, user):
        """Obtiene el menú base del sistema"""
        base_menu = [
            {
                'name': 'dashboard',
                'label': 'Dashboard',
                'url': 'core:dashboard',
                'icon': 'fas fa-tachometer-alt',
                'permission': 'core.view_dashboard',
                'order': 1
            },
            {
                'name': 'system',
                'label': 'System',
                'icon': 'fas fa-cogs',
                'permission': 'core.view_system',
                'order': 100,
                'children': [
                    {
                        'name': 'modules',
                        'label': 'Module Management',
                        'url': 'core:module_list',
                        'permission': 'core.change_moduleconfig',
                        'icon': 'fas fa-puzzle-piece'
                    },
                    {
                        'name': 'users',
                        'label': 'Users',
                        'url': 'core:user_list',
                        'permission': 'core.view_usuario',
                        'icon': 'fas fa-users'
                    },
                    {
                        'name': 'roles',
                        'label': 'Roles',
                        'url': 'core:role_list',
                        'permission': 'core.view_rol',
                        'icon': 'fas fa-user-tag'
                    },
                    {
                        'name': 'permissions',
                        'label': 'Permissions',
                        'url': 'core:permission_list',
                        'permission': 'core.view_permiso',
                        'icon': 'fas fa-key'
                    }
                ]
            }
        ]
        
        return self.filter_menu_by_permissions(base_menu, user)
    
    def user_has_module_access(self, user, module_name):
        """Verifica si el usuario tiene acceso al módulo"""
        # Administradores tienen acceso total
        if user.is_superuser or user.is_admin():
            return True
        
        # Verificar permisos específicos del módulo
        from core.module_registry import MODULE_CONFIGS
        config = MODULE_CONFIGS.get(module_name, {})
        permissions = config.get('permissions', [])
        
        if not permissions:
            # Si no hay permisos definidos, permitir acceso
            return True
        
        # Verificar si el usuario tiene al menos un permiso del módulo
        for permission in permissions:
            if user.tiene_permiso(permission):
                return True
        
        return False
    
    def filter_menu_by_permissions(self, menu_config, user):
        """Filtra el menú según los permisos del usuario"""
        filtered_menu = []
        
        for item in menu_config:
            # Verificar si el usuario tiene permiso para este ítem
            if 'permission' in item:
                if not user.tiene_permiso(item['permission']):
                    continue
            
            # Procesar hijos recursivamente
            if 'children' in item:
                filtered_children = self.filter_menu_by_permissions(item['children'], user)
                if filtered_children:
                    item_copy = item.copy()
                    item_copy['children'] = filtered_children
                    filtered_menu.append(item_copy)
            else:
                filtered_menu.append(item)
        
        return filtered_menu
    
    def get_module_menu_items(self, module_name, user):
        """Obtiene los ítems de menú de un módulo específico"""
        if module_name not in self.module_menus:
            return []
        
        menu_config = self.module_menus[module_name]
        return self.filter_menu_by_permissions(menu_config, user)
    
    def reload_module_menus(self):
        """Recarga los menús de módulos"""
        self.module_menus = {}
        self.load_module_menus()
        # Limpiar cache de menús
        cache.delete_pattern('user_menu_*')
    
    def get_menu_summary(self, user):
        """Obtiene un resumen del menú del usuario"""
        menu = self.get_user_menu(user)
        
        summary = {
            'total_items': len(menu),
            'modules': {},
            'permissions_required': set()
        }
        
        def analyze_menu_items(items, parent_name=''):
            for item in items:
                module_name = parent_name or item.get('module', 'unknown')
                
                if module_name not in summary['modules']:
                    summary['modules'][module_name] = {
                        'items': 0,
                        'children': 0
                    }
                
                summary['modules'][module_name]['items'] += 1
                
                if 'permission' in item:
                    summary['permissions_required'].add(item['permission'])
                
                if 'children' in item:
                    summary['modules'][module_name]['children'] += len(item['children'])
                    analyze_menu_items(item['children'], module_name)
        
        analyze_menu_items(menu)
        summary['permissions_required'] = list(summary['permissions_required'])
        
        return summary
    
    def validate_menu_config(self, module_name):
        """Valida la configuración de menú de un módulo"""
        try:
            menu_config = self.get_module_menu(module_name)
            
            for item in menu_config:
                # Verificar campos requeridos
                if 'name' not in item:
                    return False, f"Menu item missing 'name' in {module_name}"
                
                if 'label' not in item:
                    return False, f"Menu item missing 'label' in {module_name}"
                
                # Verificar URLs válidas
                if 'url' in item and not item['url']:
                    return False, f"Menu item has empty URL in {module_name}"
                
                # Verificar hijos recursivamente
                if 'children' in item:
                    for child in item['children']:
                        if 'name' not in child:
                            return False, f"Child menu item missing 'name' in {module_name}"
            
            return True, f"Menu configuration valid for {module_name}"
            
        except Exception as e:
            return False, f"Error validating menu for {module_name}: {str(e)}"


# Instancia global del MenuManager
menu_manager = MenuManager() 