from django.db import migrations
from django.utils import timezone


def create_cash_flow_by_account_report(apps, schema_editor):
    """Crea el reporte de Flujo de Caja por Cuentas/Cajas."""
    # Verificar si la tabla existe antes de intentar acceder
    from django.db import connection
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportdefinition'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("⚠️  Tabla reports_reportdefinition no existe, saltando creación de reporte cash_flow_by_account")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando creación de reporte cash_flow_by_account")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    report_def, _ = ReportDefinition.objects.update_or_create(
        slug="cash_flow_by_account",
        empresa=None,
        defaults={
            "name": "Flujo de Caja por Cuentas/Cajas",
            "description": "Desglose del flujo de caja por cada cuenta/caja individual. Muestra saldos iniciales, finales y movimientos por tipo de flujo (operativo, inversión, financiamiento) para cada caja o cuenta bancaria. Permite análisis detallado de la liquidez por cuenta.",
            "category": "managerial",
            "config": {
                "metrics": ["saldo_inicial", "saldo_final", "operating_flow", "investing_flow", "financing_flow", "cash_variation"],
                "dimensions": ["caja_nombre", "caja_tipo", "fecha"],
                "tags": ["cashflow", "accounts", "cajas", "liquidity", "managerial"],
                "notes": [
                    "Fuente: tabla caja y caja_abm",
                    "Agrupa movimientos por caja origen/destino",
                    "Calcula saldos iniciales y finales por caja",
                    "Clasifica movimientos en flujos operativo, inversión y financiamiento",
                ],
                "filters": {
                    "fecha_inicio": {"type": "date", "required": True, "label": "Fecha Inicio"},
                    "fecha_fin": {"type": "date", "required": True, "label": "Fecha Fin"},
                    "id_caja": {"type": "multi_select", "required": False, "label": "Caja"},
                    "dia_actual": {"type": "boolean", "required": False, "label": "Día en curso", "default": False},
                    "mes_actual": {"type": "boolean", "required": False, "label": "Mes en curso", "default": False},
                    "año_actual": {"type": "boolean", "required": False, "label": "Año en curso", "default": False},
                    "periodo_tipo": {"type": "select", "required": False, "label": "Tipo de Período", "options": ["dia_actual", "mes_actual", "año_actual", "personalizado"]},
                },
            },
            "metadata": {
                "created_by": "system",
                "seeded_at": now.isoformat(),
                "tags": ["cashflow", "accounts", "cajas", "liquidity", "managerial"],
                "related_reports": ["cash_flow_waterfall", "cash_flow_detailed_movements"],
            },
            "refresh_interval": "realtime",
            "is_active": True,
        },
    )

    # Eliminar widgets existentes y crear nuevos
    ReportWidget.objects.filter(report=report_def).delete()
    
    # Widget principal: Tabla por caja
    ReportWidget.objects.create(
        report=report_def,
        name="Tabla por Cuenta/Caja",
        widget_type="pivot-table",
        order=1,
        layout={"w": 12, "h": 8},
        configuration={
            "rows": ["caja_nombre", "caja_tipo"],
            "columns": ["period"],
            "values": ["saldo_inicial", "saldo_final", "operating_flow", "investing_flow", "financing_flow", "cash_variation"],
            "aggregation": "sum",
            "pagination": True,
            "page_size": 50,
            "sortable": True,
            "filterable": True,
            "exportable": True,
        },
    )
    
    # Widget secundario: Gráfico de barras por caja
    ReportWidget.objects.create(
        report=report_def,
        name="Gráfico por Caja",
        widget_type="d3-bar",
        order=2,
        layout={"w": 12, "h": 6},
        configuration={
            "x_axis": "caja_nombre",
            "y_axis": "cash_variation",
            "group_by": "caja_tipo",
            "stacked": False,
            "colors": ["#3b82f6", "#10b981", "#f59e0b"],
        },
    )


def delete_cash_flow_by_account_report(apps, schema_editor):
    # Verificar si la tabla existe antes de intentar acceder
    from django.db import connection
    cursor = connection.cursor()
    
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportdefinition'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("⚠️  Tabla reports_reportdefinition no existe, saltando eliminación de reporte cash_flow_by_account")
            return
    except Exception as e:
        print(f"⚠️  Error verificando tabla: {e}, saltando eliminación de reporte cash_flow_by_account")
        return
    finally:
        cursor.close()
    
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    try:
        ReportDefinition.objects.filter(slug="cash_flow_by_account", empresa__isnull=True).delete()
    except Exception as e:
        print(f"⚠️  Error eliminando reporte cash_flow_by_account: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0012_add_index_is_visible"),
    ]

    operations = [
        migrations.RunPython(create_cash_flow_by_account_report, delete_cash_flow_by_account_report),
    ]



