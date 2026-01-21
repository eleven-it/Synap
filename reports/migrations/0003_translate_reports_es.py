from django.db import migrations


REPORT_TRANSLATIONS = {
    "ventas_resumen": {
        "name": "Resumen de ventas",
        "description": "Ingresos y pedidos diarios con margen bruto y ticket promedio por canal.",
        "widgets": {
            "Revenue vs Orders trend": "Ingresos vs pedidos (tendencia)",
        },
    },
    "ventas_mix_canal": {
        "name": "Mix de ventas por canal",
        "description": "Composición de ingresos por canal y tasa de conversión semanal.",
        "widgets": {
            "Channel mix stacked bars": "Participación por canal",
        },
    },
    "ventas_ticket_medio": {
        "name": "Evolución del ticket promedio",
        "description": "Ticket promedio y transacciones con desglose por canal.",
        "widgets": {
            "Average ticket line": "Ticket promedio por día",
        },
    },
    "clientes_churn_ltv": {
        "name": "Retención y LTV de clientes",
        "description": "Clientes nuevos, reincidentes, churn y LTV por segmento.",
        "widgets": {
            "Churn vs Retention": "Churn vs retención",
        },
    },
    "inventario_rotacion_cobertura": {
        "name": "Rotación y cobertura de inventario",
        "description": "Cobertura y rotación por familia de producto y depósito.",
        "widgets": {
            "Coverage bullet chart": "Cobertura objetivo",
        },
    },
    "compras_cumplimiento": {
        "name": "Cumplimiento de proveedores",
        "description": "Órdenes, lead time, cumplimiento y variación de costos por proveedor.",
        "widgets": {
            "Lead time violins": "Lead time por proveedor",
        },
    },
    "ar_aging_dso": {
        "name": "Antigüedad de cuentas por cobrar",
        "description": "Buckets de cobranza, DSO y montos vencidos por segmento.",
        "widgets": {
            "Aging stacked bars": "Antigüedad cuentas por cobrar",
        },
    },
    "ap_aging_dpo": {
        "name": "Antigüedad de cuentas por pagar",
        "description": "Buckets de proveedores, DPO y descuentos perdidos.",
        "widgets": {
            "Payables heatmap": "Mapa de calor de proveedores",
        },
    },
    "logistica_otif": {
        "name": "Logística OTIF",
        "description": "Indicadores OTIF, tiempo de ciclo y backorders por ruta.",
        "widgets": {
            "OTIF gauge": "OTIF por ruta",
        },
    },
    "pyg_resumen": {
        "name": "PyG resumido",
        "description": "Principales líneas de ingresos, costos, margen, EBITDA y resultado neto.",
        "widgets": {
            "Waterfall P&L bridge": "Puente de resultados",
        },
    },
    "pyg_bridge": {
        "name": "Puente de ingresos a resultado",
        "description": "Variaciones desde ingresos hasta resultado neto.",
        "widgets": {
            "Bridge chart": "Puente financiero",
        },
    },
    "ebitda_trend": {
        "name": "Tendencia de EBITDA",
        "description": "Serie mensual de EBITDA vs presupuesto por unidad de negocio.",
        "widgets": {
            "EBITDA trend line": "EBITDA vs presupuesto",
        },
    },
    "liquidez_solvencia": {
        "name": "Liquidez y solvencia",
        "description": "Ratios de liquidez corriente, prueba ácida y deuda/capital.",
        "widgets": {
            "Liquidity scorecards": "Tarjetas de liquidez",
        },
    },
    "endeudamiento_cobertura": {
        "name": "Endeudamiento y cobertura",
        "description": "Indicadores de deuda total e índice de cobertura de intereses.",
        "widgets": {
            "Coverage bar chart": "Cobertura de intereses",
        },
    },
    "ccc_ciclo_efectivo": {
        "name": "Ciclo de conversión de efectivo",
        "description": "DSO, DIO y DPO con cálculo del ciclo de efectivo.",
        "widgets": {
            "CCC stacked area": "Ciclo de efectivo",
        },
    },
    "cash_flow_waterfall": {
        "name": "Flujo de caja",
        "description": "Flujos operativo, de inversión y financiamiento con variación de caja.",
        "widgets": {
            "Cash flow waterfall": "Puente de flujo de caja",
        },
    },
    "burn_runway": {
        "name": "Burn rate y runway",
        "description": "Burn rate mensual y meses de runway disponible.",
        "widgets": {
            "Runway gauge": "Runway",
        },
    },
    "presupuesto_vs_real": {
        "name": "Presupuesto vs real",
        "description": "Desviaciones absolutas y porcentuales contra presupuesto.",
        "widgets": {
            "Variance lollipop": "Desviación presupuesto",
        },
    },
}


def translate_reports(apps, schema_editor):
    # Verificar que la tabla exista antes de intentar usarla
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = 'reports_reportdefinition'
            """)
            if not cursor.fetchone():
                # La tabla no existe, saltar esta migración
                print("⚠️  Tabla reports_reportdefinition no existe, saltando traducción de reportes")
                return
    except Exception as e:
        # Si hay error verificando, intentar continuar
        print(f"⚠️  Error verificando tabla: {e}, continuando...")
    
    try:
        ReportDefinition = apps.get_model("reports", "ReportDefinition")
    except LookupError as e:
        print(f"⚠️  Error obteniendo modelo: {e}, saltando traducción")
        return
    ReportWidget = apps.get_model("reports", "ReportWidget")

    for slug, data in REPORT_TRANSLATIONS.items():
        try:
            report = ReportDefinition.objects.get(slug=slug, empresa__isnull=True)
        except ReportDefinition.DoesNotExist:
            continue

        report.name = data["name"]
        report.description = data["description"]
        report.save(update_fields=["name", "description", "updated_at"])

        widget_map = data.get("widgets", {})
        for old_name, new_name in widget_map.items():
            ReportWidget.objects.filter(report=report, name=old_name).update(name=new_name)


def reverse_translation(apps, schema_editor):
    # Verificar que la tabla exista antes de intentar usarla
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = 'reports_reportdefinition'
            """)
            if not cursor.fetchone():
                # La tabla no existe, saltar esta migración
                print("⚠️  Tabla reports_reportdefinition no existe, saltando reversión de traducción")
                return
    except Exception as e:
        # Si hay error verificando, intentar continuar
        print(f"⚠️  Error verificando tabla: {e}, continuando...")
    
    # No se implementa reversión explícita; se deja sin cambios.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0002_seed_initial_reports"),
    ]

    operations = [
        migrations.RunPython(translate_reports, reverse_translation),
    ]
