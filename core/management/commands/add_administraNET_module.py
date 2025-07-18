from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from core.models import ModuleConfig


class Command(BaseCommand):
    help = 'Agregar módulo administraNET_integration al sistema de gestión de módulos'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Agregando módulo administraNET_integration...')
        )

        # Configuración del módulo
        module_config = {
            'name': 'administraNET_integration',
            'display_name': 'Integración administraNET',
            'description': _(
                'Módulo para la integración con la base de datos de administraNET. '
                'Permite sincronizar productos, stock, clientes y pedidos entre '
                'administraNET y Synap de forma automática y configurable.'
            ),
            'version': '1.0.0',
            'author': 'Synap Development Team',
            'is_active': True,
            'is_required': False,
            'is_core': False,
            'dependencies': ['core', 'inventory', 'sales'],
            'optional_dependencies': ['tiendanube'],
            'settings': {
                'sync_interval': 30,
                'enable_logging': True,
                'log_level': 'INFO',
                'auto_sync': True,
            },
            'permissions': [
                'administraNET_integration.view_dashboard',
                'administraNET_integration.change_config',
                'administraNET_integration.view_mappings',
                'administraNET_integration.change_mappings',
                'administraNET_integration.view_logs',
                'administraNET_integration.manual_sync',
                'administraNET_integration.toggle_integration',
            ],
            'hooks': [
                'administraNET_integration.pre_sync',
                'administraNET_integration.post_sync',
                'administraNET_integration.sync_error',
            ]
        }

        try:
            # Verificar si el módulo ya existe
            existing_module = ModuleConfig.objects.filter(
                name=module_config['name']
            ).first()

            if existing_module:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  El módulo {module_config["name"]} ya existe. Actualizando configuración...'
                    )
                )
                
                # Actualizar configuración existente
                for field, value in module_config.items():
                    if hasattr(existing_module, field):
                        setattr(existing_module, field, value)
                
                existing_module.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Módulo {module_config["name"]} actualizado exitosamente'
                    )
                )
            else:
                # Crear nuevo módulo
                module = ModuleConfig.objects.create(**module_config)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Módulo {module.name} creado exitosamente'
                    )
                )

            # Mostrar información del módulo
            module = ModuleConfig.objects.get(name=module_config['name'])
            self.stdout.write('\n📋 Información del módulo:')
            self.stdout.write(f'   Nombre: {module.display_name}')
            self.stdout.write(f'   Versión: {module.version}')
            self.stdout.write(f'   Estado: {module.status_display}')
            self.stdout.write(f'   Dependencias: {", ".join(module.dependencies)}')
            self.stdout.write(f'   Permisos: {len(module.permissions)} configurados')
            self.stdout.write(f'   Hooks: {len(module.hooks)} configurados')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error agregando módulo: {e}')
            )
            raise

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Módulo administraNET_integration agregado al sistema')
        ) 