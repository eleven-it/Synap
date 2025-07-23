from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from administraNET_integration.models import SyncTimestampConfig


class Command(BaseCommand):
    help = 'Configurar parámetros de sincronización basada en timestamps'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Configurando sincronización basada en timestamps...')
        )
        self.stdout.write('=' * 60)

        configs = [
            {
                'sync_type': 'PRODUCTS',
                'enable_timestamp_resolution': True,
                'sync_all_fields': True,
                'log_conflicts': True,
            },
            {
                'sync_type': 'CUSTOMERS',
                'enable_timestamp_resolution': True,
                'sync_all_fields': True,
                'log_conflicts': True,
            },
            {
                'sync_type': 'STOCK',
                'enable_timestamp_resolution': True,
                'sync_all_fields': True,
                'log_conflicts': True,
            },
            {
                'sync_type': 'ORDERS',
                'enable_timestamp_resolution': True,
                'sync_all_fields': True,
                'log_conflicts': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for config_data in configs:
            try:
                config, created = SyncTimestampConfig.objects.get_or_create(
                    sync_type=config_data['sync_type'],
                    defaults=config_data
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Configuración creada para {config_data['sync_type']}")
                    )
                    created_count += 1
                else:
                    # Actualizar configuración existente
                    for key, value in config_data.items():
                        setattr(config, key, value)
                    config.save()
                    self.stdout.write(
                        self.style.WARNING(f"🔄 Configuración actualizada para {config_data['sync_type']}")
                    )
                    updated_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error configurando {config_data['sync_type']}: {e}")
                )

        self.stdout.write(f"\n📊 Resumen:")
        self.stdout.write(f"   ➕ Configuraciones creadas: {created_count}")
        self.stdout.write(f"   🔄 Configuraciones actualizadas: {updated_count}")
        self.stdout.write(f"   📋 Total configuraciones: {SyncTimestampConfig.objects.count()}")

        # Mostrar configuraciones actuales
        self.stdout.write("\n🔍 Configuraciones actuales:")
        self.stdout.write("-" * 60)

        try:
            configs = SyncTimestampConfig.objects.all().order_by('sync_type')

            if not configs.exists():
                self.stdout.write(
                    self.style.ERROR("❌ No hay configuraciones definidas")
                )
                return

            for config in configs:
                self.stdout.write(f"📋 {config.sync_type}:")
                self.stdout.write(f"   ✅ Timestamp resolution: {'Habilitado' if config.enable_timestamp_resolution else 'Deshabilitado'}")
                self.stdout.write(f"   🔄 Sync all fields: {'Sí' if config.sync_all_fields else 'No'}")
                self.stdout.write(f"   📝 Log conflicts: {'Sí' if config.log_conflicts else 'No'}")
                self.stdout.write(f"   📅 Última actualización: {config.updated_at.strftime('%Y-%m-%d %H:%M')}")
                self.stdout.write()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error mostrando configuraciones: {e}")
            )

        self.stdout.write(
            self.style.SUCCESS("✅ Configuración completada exitosamente!")
        )
        self.stdout.write("\n📝 Próximos pasos:")
        self.stdout.write("   1. Ejecutar script SQL en administraNET")
        self.stdout.write("   2. Probar sincronización con --dry-run")
        self.stdout.write("   3. Ejecutar sincronización real") 