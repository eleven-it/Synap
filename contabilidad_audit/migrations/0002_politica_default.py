"""Data migration: política global __default__."""
from decimal import Decimal

from django.db import migrations


def crear_politica_default(apps, schema_editor):
    Politica = apps.get_model("contabilidad_audit", "PoliticaAuditoriaContable")
    if Politica.objects.filter(base_empresa="__default__").exists():
        return
    Politica.objects.create(
        base_empresa="__default__",
        tratamiento_anulados="excluir",
        politica_centavo="diario_manda",
        prefijos_cuenta={
            "resultado": ["4"],
            "activo": ["1"],
            "pasivo": ["2"],
            "pn": ["3"],
        },
        ejercicios_cerrados="no_tocar",
        alcance_recompute="ejercicio_seleccionado",
        tolerancia_decimal=Decimal("0.005"),
        actualizado_por="sistema",
    )


def revertir_politica_default(apps, schema_editor):
    Politica = apps.get_model("contabilidad_audit", "PoliticaAuditoriaContable")
    Politica.objects.filter(base_empresa="__default__").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contabilidad_audit", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_politica_default, revertir_politica_default),
    ]
