# Filtro opcional vendedores_excluidos en informe ventas-objetivos-vs-bo (metadatos config).
from django.db import migrations


def patch_config(apps, schema_editor):
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
    for r in ReportDefinition.objects.filter(slug="ventas-objetivos-vs-bo"):
        cfg = dict(r.config or {})
        filters = dict(cfg.get("filters") or {})
        filters["vendedores_excluidos"] = {
            "type": "multi_select",
            "required": False,
            "label": "Vendedores a excluir",
        }
        cfg["filters"] = filters
        r.config = cfg
        r.save(update_fields=["config"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0031_add_ventas_objetivos_vs_bo_report"),
    ]

    operations = [
        migrations.RunPython(patch_config, noop_reverse),
    ]
