from django.db import migrations


def register_ia_module(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    module_name = "ia"

    ModuleConfig.objects.update_or_create(
        name=module_name,
        defaults={
            "display_name": "IA y Asistentes",
            "description": (
                "Plataforma de asistentes personales persistentes con memoria, "
                "orquestación multiagente y configuración de proveedores/modelos por UI."
            ),
            "version": "1.0.0",
            "author": "Synap Team",
            "is_active": True,
            "is_required": False,
            "is_core": False,
            "dependencies": ["core", "dashboard", "reports"],
            "optional_dependencies": ["stock", "ventas", "compras", "mpr", "logistica", "self_checkout"],
            "settings": {
                "memory_enabled": True,
                "provider_ui_enabled": True,
                "conversation_surface": "pwa-mobile-first",
                "default_agent_slug": "asistente-reportes",
            },
            "permissions": [
                "ia.ver",
                "ia.agentes",
                "ia.reportes",
                "ia.memoria",
                "ia.recomendaciones",
                "ia.predicciones",
                "ia.automatizacion",
                "ia.admin",
            ],
            "hooks": [
                "ia.conversation_created",
                "ia.execution_completed",
                "ia.memory_written",
            ],
        },
    )


def unregister_ia_module(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    ModuleConfig.objects.filter(name="ia").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ia", "0003_llmproviderconfig_api_key_last4_and_more"),
        ("core", "0011_moduleconfig_logistica"),
    ]

    operations = [
        migrations.RunPython(register_ia_module, unregister_ia_module),
    ]
