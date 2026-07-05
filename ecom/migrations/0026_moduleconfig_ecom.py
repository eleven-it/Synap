# Registra el módulo ecom en Module Management (BD existentes).

from django.db import migrations

from core.module_registry import MODULE_CONFIGS


def crear_moduleconfig_ecom(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    cfg = MODULE_CONFIGS["ecom"]
    ModuleConfig.objects.update_or_create(
        name="ecom",
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
            "is_active": True,
        },
    )


def revertir_moduleconfig_ecom(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    ModuleConfig.objects.filter(name="ecom").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0025_checkpoint_mayoristapp_percepciones_iibb"),
    ]

    operations = [
        migrations.RunPython(crear_moduleconfig_ecom, revertir_moduleconfig_ecom),
    ]
