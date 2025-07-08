"""
Comando para configurar y gestionar módulos del sistema Synap
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import ModuleConfig
from core.module_manager import module_manager
from core.module_registry import MODULE_CONFIGS
from core.dependency_manager import dependency_manager
from core.menu_manager import menu_manager
from core.hook_manager import hook_manager
from core.hook_registry import hook_registry
from core.event_dispatcher import event_dispatcher
from core.event_listeners import event_listener_manager
from core.plugin_manager import plugin_manager
from core.plugin_registry import plugin_registry
from core.extension_manager import extension_manager


class Command(BaseCommand):
    help = 'Setup and configure system modules'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all module configurations'
        )
        parser.add_argument(
            '--activate',
            nargs='+',
            help='Modules to activate'
        )
        parser.add_argument(
            '--deactivate',
            nargs='+',
            help='Modules to deactivate'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all modules and their status'
        )
        parser.add_argument(
            '--info',
            nargs='+',
            help='Show detailed information about specific modules'
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate module dependencies'
        )
        parser.add_argument(
            '--init',
            action='store_true',
            help='Initialize default module configuration'
        )
        parser.add_argument(
            '--menus',
            action='store_true',
            help='Show menu information for modules'
        )
        parser.add_argument(
            '--validate-menus',
            action='store_true',
            help='Validate menu configurations'
        )
        parser.add_argument(
            '--reload-menus',
            action='store_true',
            help='Reload menu configurations'
        )
        parser.add_argument(
            '--hooks',
            action='store_true',
            help='Show hook information for modules'
        )
        parser.add_argument(
            '--validate-hooks',
            action='store_true',
            help='Validate hook configurations'
        )
        parser.add_argument(
            '--reload-hooks',
            action='store_true',
            help='Reload hook configurations'
        )
        parser.add_argument(
            '--events',
            action='store_true',
            help='Show event information for modules'
        )
        parser.add_argument(
            '--test-hooks',
            action='store_true',
            help='Test hook system with sample events'
        )
        parser.add_argument(
            '--plugins',
            action='store_true',
            help='Show plugin information for modules'
        )
        parser.add_argument(
            '--validate-plugins',
            action='store_true',
            help='Validate plugin configurations'
        )
        parser.add_argument(
            '--reload-plugins',
            action='store_true',
            help='Reload plugin configurations'
        )
        parser.add_argument(
            '--extensions',
            action='store_true',
            help='Show extension information for modules'
        )
        parser.add_argument(
            '--validate-extensions',
            action='store_true',
            help='Validate extension configurations'
        )
        parser.add_argument(
            '--reload-extensions',
            action='store_true',
            help='Reload extension configurations'
        )
        parser.add_argument(
            '--test-plugins',
            action='store_true',
            help='Test plugin system with sample plugins'
        )
        parser.add_argument(
            '--test-extensions',
            action='store_true',
            help='Test extension system with sample extensions'
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.reset_modules()
        
        if options['init']:
            self.init_modules()
        
        if options['activate']:
            self.activate_modules(options['activate'])
        
        if options['deactivate']:
            self.deactivate_modules(options['deactivate'])
        
        if options['list']:
            self.list_modules()
        
        if options['info']:
            self.show_module_info(options['info'])
        
        if options['validate']:
            self.validate_dependencies()
        
        if options['menus']:
            self.show_menu_info()
        
        if options['validate_menus']:
            self.validate_menus()
        
        if options['reload_menus']:
            self.reload_menus()
        
        if options['hooks']:
            self.show_hook_info()
        
        if options['validate_hooks']:
            self.validate_hooks()
        
        if options['reload_hooks']:
            self.reload_hooks()
        
        if options['events']:
            self.show_event_info()
        
        if options['test_hooks']:
            self.test_hooks()
        
        # Si no se especificó ninguna opción, mostrar ayuda
        if not any([options['reset'], options['init'], options['activate'], 
                   options['deactivate'], options['list'], options['info'], 
                   options['validate'], options['menus'], options['validate_menus'],
                   options['reload_menus'], options['hooks'], options['validate_hooks'],
                   options['reload_hooks'], options['events'], options['test_hooks']]):
            self.stdout.write(self.style.WARNING('No action specified. Use --help for options.'))
    
    def reset_modules(self):
        """Resetea la configuración de módulos"""
        self.stdout.write('Resetting module configurations...')
        
        with transaction.atomic():
            ModuleConfig.objects.all().delete()
            
            for module_name, config in MODULE_CONFIGS.items():
                ModuleConfig.objects.create(
                    name=module_name,
                    display_name=config['display_name'],
                    description=config['description'],
                    version=config['version'],
                    author=config.get('author', ''),
                    is_required=config.get('is_required', False),
                    is_core=config.get('is_core', False),
                    dependencies=config.get('dependencies', []),
                    optional_dependencies=config.get('optional_dependencies', []),
                    settings=config.get('settings', {}),
                    permissions=config.get('permissions', []),
                    hooks=config.get('hooks', []),
                    is_active=config.get('is_required', False),  # Solo activar módulos requeridos
                )
        
        # Recargar menús y hooks después del reset
        menu_manager.reload_module_menus()
        hook_manager.reload_hooks()
        hook_registry.reload_registry()
        event_listener_manager.reload_listeners()
        
        self.stdout.write(
            self.style.SUCCESS('Module configurations reset successfully')
        )
    
    def init_modules(self):
        """Inicializa la configuración por defecto de módulos"""
        self.stdout.write('Initializing default module configuration...')
        
        # Verificar si ya existen configuraciones
        if ModuleConfig.objects.exists():
            self.stdout.write(
                self.style.WARNING('Module configurations already exist. Use --reset to clear them.')
            )
            return
        
        with transaction.atomic():
            for module_name, config in MODULE_CONFIGS.items():
                ModuleConfig.objects.create(
                    name=module_name,
                    display_name=config['display_name'],
                    description=config['description'],
                    version=config['version'],
                    author=config.get('author', ''),
                    is_required=config.get('is_required', False),
                    is_core=config.get('is_core', False),
                    dependencies=config.get('dependencies', []),
                    optional_dependencies=config.get('optional_dependencies', []),
                    settings=config.get('settings', {}),
                    permissions=config.get('permissions', []),
                    hooks=config.get('hooks', []),
                    is_active=config.get('is_required', False),  # Solo activar módulos requeridos
                )
        
        # Recargar menús y hooks después de la inicialización
        menu_manager.reload_module_menus()
        hook_manager.reload_hooks()
        hook_registry.reload_registry()
        event_listener_manager.reload_listeners()
        
        self.stdout.write(
            self.style.SUCCESS('Default module configuration initialized successfully')
        )
    
    def activate_modules(self, modules):
        """Activa módulos específicos"""
        self.stdout.write(f'Activating modules: {", ".join(modules)}')
        
        # Obtener orden de activación
        activation_order = dependency_manager.get_activation_order(modules)
        
        for module in activation_order:
            if module in modules:  # Solo activar los módulos solicitados
                success, message = module_manager.activate_module(module)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Module {module} activated')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Could not activate module {module}: {message}')
                    )
        
        # Recargar menús y hooks después de activar módulos
        menu_manager.reload_module_menus()
        hook_manager.reload_hooks()
        hook_registry.reload_registry()
        event_listener_manager.reload_listeners()
    
    def deactivate_modules(self, modules):
        """Desactiva módulos específicos"""
        self.stdout.write(f'Deactivating modules: {", ".join(modules)}')
        
        # Obtener orden de desactivación
        deactivation_order = dependency_manager.get_deactivation_order(modules)
        
        for module in deactivation_order:
            if module in modules:  # Solo desactivar los módulos solicitados
                success, message = module_manager.deactivate_module(module)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Module {module} deactivated')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Could not deactivate module {module}: {message}')
                    )
        
        # Recargar menús y hooks después de desactivar módulos
        menu_manager.reload_module_menus()
        hook_manager.reload_hooks()
        hook_registry.reload_registry()
        event_listener_manager.reload_listeners()
    
    def list_modules(self):
        """Lista todos los módulos y su estado"""
        self.stdout.write('\nModule Status Summary:')
        self.stdout.write('=' * 80)
        
        # Obtener resumen
        summary = module_manager.get_modules_summary()
        
        self.stdout.write(f'Total modules: {summary["total_modules"]}')
        self.stdout.write(f'Active modules: {summary["active_modules"]}')
        self.stdout.write(f'Core modules: {summary["core_modules"]}')
        self.stdout.write(f'Required modules: {summary["required_modules"]}')
        self.stdout.write(f'Optional modules: {summary["optional_modules"]}')
        
        self.stdout.write('\nDetailed Module List:')
        self.stdout.write('-' * 80)
        
        for module_info in summary['modules']:
            status_icon = '✓' if module_info['is_active'] else '✗'
            status_color = self.style.SUCCESS if module_info['is_active'] else self.style.ERROR
            
            self.stdout.write(
                f'{status_icon} {module_info["name"]:<20} '
                f'{status_color(module_info["display_name"]):<25} '
                f'v{module_info["version"]}'
            )
            
            if module_info['dependencies']:
                self.stdout.write(
                    f'    Dependencies: {", ".join(module_info["dependencies"])}'
                )
    
    def show_module_info(self, modules):
        """Muestra información detallada de módulos específicos"""
        for module_name in modules:
            self.stdout.write(f'\nModule: {module_name}')
            self.stdout.write('=' * 50)
            
            # Información del módulo
            module = ModuleConfig.objects.filter(name=module_name).first()
            if not module:
                self.stdout.write(self.style.ERROR(f'Module {module_name} not found'))
                continue
            
            self.stdout.write(f'Display Name: {module.display_name}')
            self.stdout.write(f'Description: {module.description}')
            self.stdout.write(f'Version: {module.version}')
            self.stdout.write(f'Author: {module.author}')
            self.stdout.write(f'Status: {"Active" if module.is_active else "Inactive"}')
            self.stdout.write(f'Core: {module.is_core}')
            self.stdout.write(f'Required: {module.is_required}')
            
            if module.dependencies:
                self.stdout.write(f'Dependencies: {", ".join(module.dependencies)}')
            
            if module.optional_dependencies:
                self.stdout.write(f'Optional Dependencies: {", ".join(module.optional_dependencies)}')
            
            # Estado de dependencias
            can_activate = module_manager.can_activate_module(module_name)
            can_deactivate = module_manager.can_deactivate_module(module_name)
            
            self.stdout.write(f'Can Activate: {can_activate}')
            self.stdout.write(f'Can Deactivate: {can_deactivate}')
            
            # Información de menú
            try:
                menu_config = menu_manager.get_module_menu(module_name)
                if menu_config:
                    self.stdout.write(f'Menu Items: {len(menu_config)}')
                else:
                    self.stdout.write('Menu Items: None')
            except Exception as e:
                self.stdout.write(f'Menu Items: Error - {e}')
            
            # Información de hooks
            try:
                hook_config = hook_manager.get_module_hooks(module_name)
                if hook_config:
                    self.stdout.write(f'Hooks: {len(hook_config)}')
                else:
                    self.stdout.write('Hooks: None')
            except Exception as e:
                self.stdout.write(f'Hooks: Error - {e}')
    
    def validate_dependencies(self):
        """Valida las dependencias de módulos"""
        self.stdout.write('\nValidating module dependencies...')
        self.stdout.write('=' * 50)
        
        # Verificar dependencias circulares
        if dependency_manager.check_circular_dependencies():
            self.stdout.write(self.style.ERROR('✗ Circular dependencies detected:'))
            for cycle in dependency_manager.get_circular_dependencies():
                self.stdout.write(f'    {" → ".join(cycle)} → {cycle[0]}')
        else:
            self.stdout.write(self.style.SUCCESS('✓ No circular dependencies found'))
        
        # Validar dependencias individuales
        for module_name in module_manager.get_all_modules():
            is_valid, message = dependency_manager.validate_dependencies(module_name)
            if is_valid:
                self.stdout.write(self.style.SUCCESS(f'✓ {module_name}: {message}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ {module_name}: {message}'))
    
    def show_menu_info(self):
        """Muestra información de menús de módulos"""
        self.stdout.write('\nMenu Information:')
        self.stdout.write('=' * 50)
        
        for module_name in module_manager.get_active_modules():
            self.stdout.write(f'\nModule: {module_name}')
            self.stdout.write('-' * 30)
            
            try:
                menu_config = menu_manager.get_module_menu(module_name)
                if menu_config:
                    self.stdout.write(f'Menu Items: {len(menu_config)}')
                    for item in menu_config:
                        self.stdout.write(f'  - {item.get("label", "Unnamed")} ({item.get("name", "no-name")})')
                        if item.get('children'):
                            for child in item['children']:
                                self.stdout.write(f'    └─ {child.get("label", "Unnamed")} ({child.get("name", "no-name")})')
                else:
                    self.stdout.write('Menu Items: None')
            except Exception as e:
                self.stdout.write(f'Menu Error: {e}')
    
    def validate_menus(self):
        """Valida las configuraciones de menú"""
        self.stdout.write('\nValidating menu configurations...')
        self.stdout.write('=' * 50)
        
        for module_name in module_manager.get_active_modules():
            is_valid, message = menu_manager.validate_menu_config(module_name)
            if is_valid:
                self.stdout.write(self.style.SUCCESS(f'✓ {module_name}: {message}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ {module_name}: {message}'))
    
    def reload_menus(self):
        """Recarga las configuraciones de menú"""
        self.stdout.write('Reloading menu configurations...')
        menu_manager.reload_module_menus()
        self.stdout.write(self.style.SUCCESS('Menu configurations reloaded successfully'))
    
    def show_hook_info(self):
        """Muestra información de hooks de módulos"""
        self.stdout.write('\nHook Information:')
        self.stdout.write('=' * 50)
        
        hook_stats = hook_manager.get_hook_info()
        self.stdout.write(f'Total Hooks: {hook_stats.get("total_hooks", 0)}')
        
        for hook_name, listeners in hook_manager.hooks.items():
            self.stdout.write(f'\nHook: {hook_name}')
            self.stdout.write(f'  Listeners: {len(listeners)}')
            for listener in listeners:
                self.stdout.write(f'    - {listener["module_name"]}: {listener["function_name"]} (priority: {listener["priority"]})')
    
    def validate_hooks(self):
        """Valida las configuraciones de hooks"""
        self.stdout.write('\nValidating hook configurations...')
        self.stdout.write('=' * 50)
        
        validation_results = hook_manager.validate_hooks()
        for result in validation_results:
            if result['type'] == 'success':
                self.stdout.write(self.style.SUCCESS(f'✓ {result["module"]}: {result["message"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ {result["module"]}: {result["message"]}'))
    
    def reload_hooks(self):
        """Recarga las configuraciones de hooks"""
        self.stdout.write('Reloading hook configurations...')
        hook_manager.reload_hooks()
        hook_registry.reload_registry()
        event_listener_manager.reload_listeners()
        self.stdout.write(self.style.SUCCESS('Hook configurations reloaded successfully'))
    
    def show_event_info(self):
        """Muestra información de eventos del sistema"""
        self.stdout.write('\nEvent Information:')
        self.stdout.write('=' * 50)
        
        event_stats = event_dispatcher.get_event_statistics()
        self.stdout.write(f'Total Events: {event_stats.get("total_events", 0)}')
        self.stdout.write(f'Queued Events: {event_stats.get("queued_events", 0)}')
        self.stdout.write(f'Is Processing: {event_stats.get("is_processing", False)}')
        
        if event_stats.get('event_counts'):
            self.stdout.write('\nEvent Counts:')
            for event_name, count in event_stats['event_counts'].items():
                self.stdout.write(f'  - {event_name}: {count}')
    
    def test_hooks(self):
        """Prueba el sistema de hooks con eventos de ejemplo"""
        self.stdout.write('\nTesting hook system...')
        self.stdout.write('=' * 50)
        
        # Importar ejemplos
        try:
            from core.examples.hook_examples import register_hook_examples, demonstrate_event_dispatching
            
            # Registrar ejemplos
            register_hook_examples()
            self.stdout.write(self.style.SUCCESS('✓ Hook examples registered'))
            
            # Demostrar event dispatching
            demonstrate_event_dispatching()
            self.stdout.write(self.style.SUCCESS('✓ Event dispatching demonstrated'))
            
        except ImportError:
            self.stdout.write(self.style.WARNING('Hook examples not available'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error testing hooks: {e}')) 