# Registra el módulo mpr en Module Management (BD existentes).

from django.db import migrations

from core.module_registry import MODULE_CONFIGS


def crear_moduleconfig_mpr(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    cfg = MODULE_CONFIGS["mpr"]
    ModuleConfig.objects.update_or_create(
        name="mpr",
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
            # Activar por defecto: instalaciones que ya usaban MPR vía core_modules.
            "is_active": True,
        },
    )


def revertir_moduleconfig_mpr(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    ModuleConfig.objects.filter(name="mpr").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_moduleconfig_fe_afip"),
    ]

    operations = [
        migrations.RunPython(crear_moduleconfig_mpr, revertir_moduleconfig_mpr),
    ]
