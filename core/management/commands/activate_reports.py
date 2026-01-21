"""
Comando para activar el módulo reports
"""
from django.core.management.base import BaseCommand
from core.module_manager import module_manager
from core.models import ModuleConfig
from django.utils import timezone


class Command(BaseCommand):
    help = 'Activa el módulo reports en la base de datos'

    def handle(self, *args, **options):
        module_name = 'reports'
        
        self.stdout.write(f"🔍 Verificando módulo '{module_name}'...")
        
        # Verificar si el módulo está activo
        if module_manager.is_module_active(module_name):
            self.stdout.write(self.style.SUCCESS(f"✅ El módulo '{module_name}' ya está activo"))
            return
        
        # Intentar activar el módulo
        self.stdout.write(f"📦 Activando módulo '{module_name}'...")
        success, message = module_manager.activate_module(module_name)
        
        if success:
            self.stdout.write(self.style.SUCCESS(f"✅ Módulo '{module_name}' activado exitosamente"))
            self.stdout.write(f"   {message}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Error al activar módulo '{module_name}': {message}"))
            
            # Intentar crear manualmente si falla
            self.stdout.write(f"🔧 Intentando crear configuración manualmente...")
            try:
                from core.module_registry import MODULE_CONFIGS
                config_data = MODULE_CONFIGS.get(module_name, {})
                
                if not config_data:
                    self.stdout.write(self.style.ERROR(f"❌ No se encontró configuración para '{module_name}' en MODULE_CONFIGS"))
                    return
                
                config, created = ModuleConfig.objects.get_or_create(
                    name=module_name,
                    defaults={
                        'display_name': config_data.get('display_name', module_name),
                        'description': config_data.get('description', ''),
                        'version': config_data.get('version', '1.0.0'),
                        'author': config_data.get('author', ''),
                        'is_required': config_data.get('is_required', False),
                        'is_core': config_data.get('is_core', False),
                        'dependencies': config_data.get('dependencies', []),
                        'optional_dependencies': config_data.get('optional_dependencies', []),
                        'settings': config_data.get('settings', {}),
                        'permissions': config_data.get('permissions', []),
                        'hooks': config_data.get('hooks', []),
                        'is_active': True,
                        'last_activated': timezone.now(),
                    }
                )
                
                if not created:
                    config.is_active = True
                    config.last_activated = timezone.now()
                    config.save()
                    self.stdout.write(self.style.SUCCESS(f"✅ Configuración actualizada para '{module_name}'"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"✅ Configuración creada para '{module_name}'"))
                
                # Recargar módulos
                module_manager.load_modules()
                
                if module_manager.is_module_active(module_name):
                    self.stdout.write(self.style.SUCCESS(f"✅ Módulo '{module_name}' ahora está activo"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ Módulo '{module_name}' creado pero no se pudo verificar como activo"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error al crear configuración: {e}"))

