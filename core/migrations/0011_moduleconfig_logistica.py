# Generated manually — registra el módulo logistica en Module Management (BD existentes).

from django.db import migrations

from core.module_registry import MODULE_CONFIGS


def crear_moduleconfig_logistica(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    cfg = MODULE_CONFIGS["logistica"]
    ModuleConfig.objects.update_or_create(
        name="logistica",
        defaults={
            "display_name": cfg["display_name"],
            "description": cfg["description"],
            "version": cfg["version"],
            "author": cfg.get("author", ""),
            "is_required": cfg.get("is_required", False),
            "is_core": cfg.get("is_core", False),
            "dependencies": cfg.get("dependencies", []),
            "optional_dependencies": cfg.get("optional_dependencies", []),
            "settings": cfg.get("settings", {}),
            "permissions": cfg.get("permissions", []),
            "hooks": cfg.get("hooks", []),
            # No forzar is_active: el admin activa el módulo desde Module Management.
        },
    )


def revertir_moduleconfig_logistica(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    ModuleConfig.objects.filter(name="logistica").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_alter_navbarmenuglobal_items_menu_ocultos_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_moduleconfig_logistica, revertir_moduleconfig_logistica),
    ]
