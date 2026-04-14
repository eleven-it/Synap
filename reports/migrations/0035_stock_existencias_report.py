# Informe Stock y existencias (disponible alineado a BO).
from django.db import migrations
from django.utils import timezone


def create_stock_existencias_report(apps, schema_editor):
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
            print("⚠️  Tabla reports_reportdefinition no existe, saltando stock-existencias")
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
        slug="stock-existencias",
        empresa=None,
        defaults={
            "name": "Stock y existencias",
            "description": (
                "Listado de artículos con stock, reservado (PED en preparación/preparado) y disponible. "
                "El disponible sigue el mismo criterio que el informe BO vs stock (no usa saldo_pedido_cliente). "
                "Filtros: depósitos, clientes excluidos del reservado, búsqueda, orden, stock cero, marca, rubro y subrubro."
            ),
            "category": "operational",
            "config": {
                "metrics": ["stock", "reservado", "disponible"],
                "dimensions": ["articulo"],
                "tags": ["stock", "inventario", "operational", "backorder"],
                "filters": {
                    "depositos_incluidos": {"type": "multi_select", "required": False, "label": "Depósitos"},
                    "clientes_excluidos": {"type": "multi_select", "required": False, "label": "Clientes excluidos (reservado)"},
                    "busqueda": {"type": "string", "required": False, "label": "Búsqueda"},
                    "orden_columna": {"type": "string", "required": False, "label": "Orden"},
                    "incluir_stock_cero": {"type": "string", "required": False, "label": "Incluir stock cero"},
                    "codigo_marca": {"type": "integer", "required": False, "label": "Marca"},
                    "codigo_rubro": {"type": "integer", "required": False, "label": "Rubro"},
                    "id_subrubro": {"type": "integer", "required": False, "label": "Subrubro"},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "related_reports": ["bo-stock-facturacion"],
                "catalog_legacy_order": 108,
            },
            "refresh_interval": "realtime",
            "is_active": True,
        },
    )

    ReportWidget.objects.filter(report=report_def).delete()
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla stock y existencias",
        widget_type="table",
        order=1,
        layout={"w": 12, "h": 12},
        configuration={"source": "stock_existencias_detalle"},
    )


def delete_stock_existencias_report(apps, schema_editor):
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
    finally:
        cursor.close()

    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportDefinition.objects.filter(slug="stock-existencias", empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0034_punto_venta_canal_ejecutivo_y_report_resumen"),
    ]
    operations = [
        migrations.RunPython(create_stock_existencias_report, delete_stock_existencias_report),
    ]
