"""Default tratamiento_anulados → incluir_neutralizado (alineación pie/corrido/checks)."""
from django.db import migrations, models


def alinear_politicas_incluir_neutralizado(apps, schema_editor):
    """
    Alineación Conta_Info / Libro Mayor: pie (cont_*_saldo_cta), corrido
    (saldo_asiento) y checks saldo_*_vs_diario usan incluir_neutralizado.
    """
    Politica = apps.get_model("contabilidad_audit", "PoliticaAuditoriaContable")
    Politica.objects.filter(tratamiento_anulados="excluir").update(
        tratamiento_anulados="incluir_neutralizado"
    )


def revertir_politicas_excluir(apps, schema_editor):
    Politica = apps.get_model("contabilidad_audit", "PoliticaAuditoriaContable")
    Politica.objects.filter(tratamiento_anulados="incluir_neutralizado").update(
        tratamiento_anulados="excluir"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("contabilidad_audit", "0003_historial_politica_auditoria"),
    ]

    operations = [
        migrations.AlterField(
            model_name="politicaauditoriacontable",
            name="tratamiento_anulados",
            field=models.CharField(
                choices=[
                    ("excluir", "Excluir anulados"),
                    ("incluir_neutralizado", "Incluir neutralizados"),
                ],
                default="incluir_neutralizado",
                max_length=32,
            ),
        ),
        migrations.RunPython(
            alinear_politicas_incluir_neutralizado,
            revertir_politicas_excluir,
        ),
    ]
