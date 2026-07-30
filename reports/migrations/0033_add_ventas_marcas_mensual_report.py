# Generated migration: Informe Ventas marcas mensual
from django.db import migrations
from django.utils import timezone


def create_ventas_marcas_mensual_report(apps, schema_editor):
    """Crea ReportDefinition slug ventas-marcas-mensual."""
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
            print(
                "⚠️  Tabla reports_reportdefinition no existe, saltando ventas-marcas-mensual"
            )
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}")
        return
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="ventas-marcas-mensual",
        empresa=None,
        defaults={
            "name": "Ventas marcas mensual",
            "description": (
                "Matriz mensual vendedor → cliente por marca: unidades (packs o docenas) "
                "y facturación neta. Filtros por período, marca, SuperArt, sucursal y clientes/vendedores."
            ),
            "category": "operational",
            "config": {
                "metrics": ["unidades", "facturacion", "precio_medio"],
                "dimensions": ["vendedor", "cliente", "anio_mes"],
                "tags": ["ventas", "marcas", "mensual", "listados"],
                "catalog_legacy_section": "listados",
                "filters": {
                    "fecha_inicio_facturacion": {
                        "type": "date",
                        "required": True,
                        "label": "Fecha inicio",
                    },
                    "fecha_fin_facturacion": {
                        "type": "date",
                        "required": True,
                        "label": "Fecha fin",
                    },
                    "marcas_incluidos": {
                        "type": "multi_select",
                        "required": False,
                        "label": "Marcas",
                    },
                    "superarts_incluidos": {
                        "type": "multi_select",
                        "required": False,
                        "label": "SuperArt",
                    },
                    "modo_unidades": {
                        "type": "select",
                        "required": False,
                        "label": "Unidades",
                        "options": ["packs", "docenas"],
                        "default": "packs",
                    },
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "catalog_legacy_section": "listados",
            },
            "refresh_interval": "daily",
            "is_active": True,
        },
    )

    # show_in_catalog puede no estar en el estado histórico del modelo (columna vía SQL en 0021).
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            UPDATE reports_reportdefinition
            SET show_in_catalog = TRUE
            WHERE slug = %s AND empresa_id IS NULL
            """,
            ["ventas-marcas-mensual"],
        )
    except Exception as e:
        print(f"⚠️  No se pudo setear show_in_catalog: {e}")
    finally:
        cursor.close()

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Matriz ventas marcas",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 10},
        configuration={"view": "matriz_mensual"},
    )


def delete_ventas_marcas_mensual_report(apps, schema_editor):
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
    ReportDefinition.objects.filter(slug="ventas-marcas-mensual", empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0032_add_dabra_consolidado_remitos_report"),
    ]

    operations = [
        migrations.RunPython(
            create_ventas_marcas_mensual_report,
            delete_ventas_marcas_mensual_report,
        ),
    ]
