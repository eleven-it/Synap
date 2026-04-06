# Cierra checkpoint informes ventas netas relay v1 ampliado

from django.db import migrations


NOTAS_VN = (
    "Informes ventas netas relay v1 ampliado: GET …/api/reports/ventas-netas/relay/ "
    "(listarPor mes/cliente/vendedor/rubro/subrubro/articulo/marca/zona/tipocliente/proveedor; "
    "tipo monto/unidades/peso en dimensiones stock; grafico=1; queInforme=seleccion). "
    "Ver docs/ecom/SPEC_VENTAS_NETAS.md."
)

NOTAS_VN_GERENCIA = (
    "Informes ventas netas gerencia relay v1 ampliado: GET …/api/reports/ventas-netas/relay/gerencia/ "
    "(vt/ut/uti, listarPor mes/cliente/vendedor/rubro/subrubro/articulo/marca/zona/tipocliente/proveedor; "
    "tipo monto/unidades/peso en dimensiones stock; grafico=1; queInforme=seleccion). "
    "Ver docs/ecom/SPEC_VENTAS_NETAS.md."
)


def adelante(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_informes_vn",
        defaults={"notes": NOTAS_VN},
    )
    EcomMigrationCheckpoint.objects.update_or_create(
        module_slug="mayoristapp_informes_vn_gerencia",
        defaults={"notes": NOTAS_VN_GERENCIA},
    )


def atras(apps, schema_editor):
    EcomMigrationCheckpoint = apps.get_model("ecom", "EcomMigrationCheckpoint")
    EcomMigrationCheckpoint.objects.filter(
        module_slug__in=["mayoristapp_informes_vn", "mayoristapp_informes_vn_gerencia"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ecom", "0013_ecommailqueue"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
    ]
