# Registra tiendanube_administranet y corrige módulos huérfanos (app no instalada).

from django.apps import apps as django_apps
from django.db import migrations

from core.module_registry import MODULE_CONFIGS

# Apps comentadas en INSTALLED_APPS pero aún en MODULE_CONFIGS
MODULOS_SIN_APP_INSTALADA = ("mercadopago", "clover")


def crear_moduleconfig_tiendanube(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    cfg = MODULE_CONFIGS["tiendanube_administranet"]
    ModuleConfig.objects.update_or_create(
        name="tiendanube_administranet",
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
            # Opt-in: la integración no es parte del bootstrap mínimo.
            "is_active": False,
        },
    )


def desactivar_modulos_sin_app(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    for nombre in MODULOS_SIN_APP_INSTALADA:
        if not _app_instalada(nombre):
            ModuleConfig.objects.filter(name=nombre, is_active=True).update(is_active=False)


def _app_instalada(app_label: str) -> bool:
    try:
        return django_apps.is_installed(app_label)
    except Exception:
        return False


def revertir_moduleconfig_tiendanube(apps, schema_editor):
    ModuleConfig = apps.get_model("core", "ModuleConfig")
    ModuleConfig.objects.filter(name="tiendanube_administranet").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_moduleconfig_mpr"),
    ]

    operations = [
        migrations.RunPython(crear_moduleconfig_tiendanube, revertir_moduleconfig_tiendanube),
        migrations.RunPython(desactivar_modulos_sin_app, migrations.RunPython.noop),
    ]
