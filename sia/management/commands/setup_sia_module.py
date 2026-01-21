"""
Comando para registrar y activar el módulo SIA en el sistema
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import ModuleConfig
from core.module_registry import MODULE_CONFIGS
from django.utils import timezone


class Command(BaseCommand):
    help = 'Registra y activa el módulo SIA en ModuleConfig'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar reactivación aunque ya esté activo',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        force = options.get('force', False)
        
        if 'sia' not in MODULE_CONFIGS:
            self.stdout.write(
                self.style.ERROR('❌ SIA no está definido en MODULE_CONFIGS')
            )
            return
        
        sia_config = MODULE_CONFIGS['sia']
        
        try:
            module_config, created = ModuleConfig.objects.get_or_create(
                name='sia',
                defaults={
                    'display_name': sia_config['display_name'],
                    'description': sia_config['description'],
                    'version': sia_config['version'],
                    'author': sia_config.get('author', 'Synap Team'),
                    'is_required': sia_config.get('is_required', False),
                    'is_core': sia_config.get('is_core', False),
                    'dependencies': sia_config.get('dependencies', []),
                    'optional_dependencies': sia_config.get('optional_dependencies', []),
                    'settings': sia_config.get('settings', {}),
                    'permissions': sia_config.get('permissions', []),
                    'hooks': sia_config.get('hooks', []),
                    'is_active': True,
                    'last_activated': timezone.now(),
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Módulo SIA creado y activado')
                )
            else:
                if not module_config.is_active or force:
                    module_config.is_active = True
                    module_config.last_activated = timezone.now()
                    # Actualizar otros campos si han cambiado
                    module_config.display_name = sia_config['display_name']
                    module_config.description = sia_config['description']
                    module_config.version = sia_config['version']
                    module_config.dependencies = sia_config.get('dependencies', [])
                    module_config.optional_dependencies = sia_config.get('optional_dependencies', [])
                    module_config.settings = sia_config.get('settings', {})
                    module_config.permissions = sia_config.get('permissions', [])
                    module_config.hooks = sia_config.get('hooks', [])
                    module_config.save()
                    
                    if force:
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Módulo SIA reactivado')
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Módulo SIA activado')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Módulo SIA ya está activo. Usa --force para reactivar.')
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al configurar módulo SIA: {e}')
            )
            raise













