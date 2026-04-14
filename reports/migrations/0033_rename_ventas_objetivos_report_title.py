# Título visible del informe: "Objetivos de ventas por vendedor".
from django.db import migrations


def rename_title(apps, schema_editor):
    from django.db import connection

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'reports_reportdefinition'
            );
            """
        )
        if not cursor.fetchone()[0]:
            return
    except Exception:
        return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(slug="ventas-objetivos-vs-bo").update(
        name="Objetivos de ventas por vendedor",
        description=(
            "Seguimiento de objetivos por cliente agrupados por vendedor, con facturación, remitos, "
            "total, falta, unidades vendidas y columnas de backorder. Misma temporalidad dual que el informe BO."
        ),
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0032_ventas_objetivos_filtro_vendedores_excluidos"),
    ]

    operations = [
        migrations.RunPython(rename_title, noop_reverse),
    ]
