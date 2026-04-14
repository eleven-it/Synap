from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from core.models import ModuleConfig


class Command(BaseCommand):
    help = 'Agregar módulo tiendanube_administranet al sistema de gestión de módulos'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Agregando módulo tiendanube_administranet...')
        )

        # Configuración del módulo
        module_config = {
            'name': 'tiendanube_administranet',
            'display_name': 'Tiendanube-AdministraNET Integration',
            'description': _(
                'Integración completa entre Tiendanube y AdministraNET: sincronización de clientes, productos, órdenes y más.'
            ),
            'version': '1.0.0',
            'author': 'Synap Development Team',
            'is_active': True,
            'is_required': False,
            'is_core': False,
            'dependencies': ['core'],
            'optional_dependencies': [],
            'settings': {
                'enable_customer_sync': True,
                'enable_product_sync': True,
                'enable_order_sync': True,
                'sync_interval': 300,
                'enable_logging': True,
                'log_level': 'INFO',
            },
            'permissions': [
                'tiendanube_administranet.view_tiendanubeconfig',
                'tiendanube_administranet.add_tiendanubeconfig',
                'tiendanube_administranet.change_tiendanubeconfig',
                'tiendanube_administranet.delete_tiendanubeconfig',
                'tiendanube_administranet.view_administranetconfig',
                'tiendanube_administranet.add_administranetconfig',
                'tiendanube_administranet.change_administranetconfig',
                'tiendanube_administranet.delete_administranetconfig',
                'tiendanube_administranet.view_customermapping',
                'tiendanube_administranet.add_customermapping',
                'tiendanube_administranet.change_customermapping',
                'tiendanube_administranet.delete_customermapping',
                'tiendanube_administranet.view_productmapping',
                'tiendanube_administranet.add_productmapping',
                'tiendanube_administranet.change_productmapping',
                'tiendanube_administranet.delete_productmapping',
                'tiendanube_administranet.view_ordermapping',
                'tiendanube_administranet.add_ordermapping',
                'tiendanube_administranet.change_ordermapping',
                'tiendanube_administranet.delete_ordermapping',
                'tiendanube_administranet.view_synclog',
                'tiendanube_administranet.run_sync',
                'tiendanube_administranet.configure_mapping',
            ],
            'hooks': [
                'tiendanube_administranet.pre_customer_sync',
                'tiendanube_administranet.post_customer_sync',
                'tiendanube_administranet.pre_product_sync',
                'tiendanube_administranet.post_product_sync',
                'tiendanube_administranet.pre_order_sync',
                'tiendanube_administranet.post_order_sync',
                'tiendanube_administranet.sync_error',
                'tiendanube_administranet.sync_completed',
            ]
        }

        try:
            # Verificar si el módulo ya existe
            existing_module = ModuleConfig.objects.filter(name=module_config['name']).first()
            
            if existing_module:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  El módulo {module_config["name"]} ya existe en el sistema.')
                )
                
                # Actualizar configuración existente
                for field, value in module_config.items():
                    if hasattr(existing_module, field):
                        setattr(existing_module, field, value)
                
                existing_module.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Módulo {module_config["name"]} actualizado correctamente.')
                )
            else:
                # Crear nuevo módulo
                ModuleConfig.objects.create(**module_config)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Módulo {module_config["name"]} agregado correctamente.')
                )

            self.stdout.write(
                self.style.SUCCESS('🎉 Proceso completado exitosamente!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al agregar el módulo: {str(e)}')
            ) 