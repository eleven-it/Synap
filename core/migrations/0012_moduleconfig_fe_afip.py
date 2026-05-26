# Registra el módulo fe_afip en Module Management (BD existentes).

from django.db import migrations

from core.module_registry import MODULE_CONFIGS


def crear_moduleconfig_fe_afip(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    cfg = MODULE_CONFIGS["fe_afip"]
    ModuleConfig.objects.update_or_create(
        name="fe_afip",
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
            # Activar por defecto: sin esto /fe_afip/ queda bloqueado por ModuleMiddleware.
            "is_active": True,
        },
    )


def revertir_moduleconfig_fe_afip(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    ModuleConfig.objects.filter(name="fe_afip").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_moduleconfig_logistica"),
    ]

    operations = [
        migrations.RunPython(crear_moduleconfig_fe_afip, revertir_moduleconfig_fe_afip),
    ]
