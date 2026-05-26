"""
Comando para agregar el módulo Reports AI al sistema
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import ModuleConfig
from core.module_registry import MODULE_CONFIGS
try:
    from core.menu_manager import menu_manager
    from core.hook_manager import hook_manager
    from core.hook_registry import hook_registry
except ImportError:
    menu_manager = None
    hook_manager = None
    hook_registry = None


class Command(BaseCommand):
    help = 'Agrega el módulo Reports AI al sistema de gestión de módulos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Registrando módulo Reports AI...'))
        
        try:
            with transaction.atomic():
                module_name = 'reports_ai'
                config = MODULE_CONFIGS[module_name]
                
                # Crear o actualizar configuración del módulo
                module_config, created = ModuleConfig.objects.update_or_create(
                    name=module_name,
                    defaults={
                        'display_name': config['display_name'],
                        'description': config['description'],
                        'version': config['version'],
                        'author': config.get('author', ''),
                        'is_required': config.get('is_required', False),
                        'is_core': config.get('is_core', False),
                        'dependencies': config.get('dependencies', []),
                        'optional_dependencies': config.get('optional_dependencies', []),
                        'settings': config.get('settings', {}),
                        'permissions': config.get('permissions', []),
                        'hooks': config.get('hooks', []),
                        'is_active': False,  # Desactivado por defecto
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✓ Módulo {module_name} creado'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'✓ Módulo {module_name} actualizado'))
                
                # Recargar menús y hooks si están disponibles
                if menu_manager:
                    menu_manager.reload_module_menus()
                if hook_manager:
                    hook_manager.reload_hooks()
                if hook_registry:
                    hook_registry.reload_registry()
                
                self.stdout.write(
                    self.style.SUCCESS('\n✅ Módulo Reports AI registrado exitosamente')
                )
                self.stdout.write(
                    self.style.WARNING('\n⚠️  El módulo está DESACTIVADO por defecto')
                )
                self.stdout.write(
                    '\nPara activarlo ejecuta:'
                )
                self.stdout.write(
                    self.style.HTTP_INFO('    docker exec Synap_app python manage.py setup_modules --activate reports_ai')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Error registrando módulo: {e}')
            )
            raise

