from django.db import migrations
from django.utils import timezone


def create_report_definitions(apps, schema_editor):
    """Crea los reportes base descritos en desarrollo_reportes.md."""
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")

    now = timezone.now()

    definitions = [
        {
            "slug": "ventas_resumen",
            "name": "Sales Performance Overview",
            "category": "operational",
            "description": "Daily revenue, orders and gross margin with quick channel breakdown.",
            "refresh_interval": "daily",
            "config": {
                "metrics": ["revenue", "orders", "gross_margin", "avg_ticket"],
                "dimensions": ["date", "channel", "segment"],
                "tags": ["sales", "performance", "daily"],
                "notes": ["Source: view_fin_ventas_diaria"],
            },
            "widgets": [
                {
                    "name": "Revenue vs Orders trend",
                    "widget_type": "d3-line-area",
                    "layout": {"w": 6, "h": 4},
                    "configuration": {
                        "x_field": "date",
                        "y_fields": ["revenue", "orders"],
                        "unit": "ARS",
                    },
                },
            ],
        },
        {
            "slug": "ventas_mix_canal",
            "name": "Sales Mix by Channel",
            "category": "operational",
            "description": "Channel mix and conversion KPI across online, retail and wholesale.",
            "refresh_interval": "daily",
            "config": {
                "metrics": ["revenue", "orders", "conversion_rate"],
                "dimensions": ["channel", "week"],
                "tags": ["sales", "mix", "channel"],
            },
            "widgets": [
                {
                    "name": "Channel mix stacked bars",
                    "widget_type": "d3-bar-stacked",
                    "layout": {"w": 6, "h": 4},
                    "configuration": {"x_field": "channel", "y_field": "revenue"},
                },
            ],
        },
        {
            "slug": "ventas_ticket_medio",
            "name": "Average Ticket Evolution",
            "category": "operational",
            "description": "Average ticket and transactions trend with drill by channel.",
            "refresh_interval": "daily",
            "config": {
                "metrics": ["avg_ticket", "transactions"],
                "dimensions": ["date", "channel"],
                "tags": ["sales", "ticket"],
            },
            "widgets": [
                {
                    "name": "Average ticket line",
                    "widget_type": "d3-line",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "date", "y_field": "avg_ticket"},
                },
            ],
        },
        {
            "slug": "clientes_churn_ltv",
            "name": "Customer Retention & LTV",
            "category": "operational",
            "description": "Retention, churn and lifetime value estimations by segment.",
            "refresh_interval": "weekly",
            "config": {
                "metrics": ["churn_rate", "retention_rate", "ltv"],
                "dimensions": ["month"],
                "tags": ["customers", "retention"],
            },
            "widgets": [
                {
                    "name": "Churn vs Retention Connected",
                    "widget_type": "d3-connected-scatter",
                    "layout": {"w": 6, "h": 4},
                    "configuration": {
                        "x_field": "retention_rate",
                        "y_field": "churn_rate",
                        "label_field": "month",
                        "radius_field": "ltv",
                    },
                },
            ],
        },
        {
            "slug": "inventario_rotacion_cobertura",
            "name": "Inventory Rotation & Coverage",
            "category": "operational",
            "description": "Rotation, coverage and stock-outs tracking per product family.",
            "refresh_interval": "daily",
            "config": {
                "metrics": ["stock", "rotation_days", "coverage_days"],
                "dimensions": ["product_family", "warehouse"],
                "tags": ["inventory", "stock"],
            },
            "widgets": [
                {
                    "name": "Coverage bullet chart",
                    "widget_type": "d3-bullet",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"value_field": "coverage_days", "target": 30},
                },
            ],
        },
        {
            "slug": "compras_cumplimiento",
            "name": "Supplier Compliance",
            "category": "operational",
            "description": "Purchase orders cycle time and supplier compliance rate.",
            "refresh_interval": "weekly",
            "config": {
                "metrics": ["orders", "lead_time", "compliance_rate", "unit_cost_variance"],
                "dimensions": ["supplier", "month"],
                "tags": ["purchases", "suppliers"],
            },
            "widgets": [
                {
                    "name": "Lead time violins",
                    "widget_type": "d3-line",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "month", "y_field": "lead_time"},
                },
            ],
        },
        {
            "slug": "ar_aging_dso",
            "name": "Accounts Receivable Aging",
            "category": "operational",
            "description": "Receivables by bucket and Days Sales Outstanding indicator.",
            "refresh_interval": "daily",
            "config": {
                "metrics": ["balance", "dso", "overdue_amount"],
                "dimensions": ["aging_bucket", "customer_segment"],
                "tags": ["finance", "ar"],
            },
            "widgets": [
                {
                    "name": "Aging stacked bars",
                    "widget_type": "d3-bar-stacked",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "aging_bucket", "y_field": "balance"},
                },
            ],
        },
        {
            "slug": "ap_aging_dpo",
            "name": "Accounts Payable Aging",
            "category": "operational",
            "description": "Supplier payables buckets and Days Payables Outstanding trends.",
            "refresh_interval": "daily",
            "config": {
                "metrics": ["balance", "dpo", "discounts_lost"],
                "dimensions": ["aging_bucket", "supplier_group"],
                "tags": ["finance", "ap"],
            },
            "widgets": [
                {
                    "name": "Payables heatmap",
                    "widget_type": "d3-heatmap",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "aging_bucket", "y_field": "supplier_group", "value_field": "balance"},
                },
            ],
        },
        {
            "slug": "logistica_otif",
            "name": "Logistics OTIF",
            "category": "operational",
            "description": "On-time in-full and cycle time per route and branch.",
            "refresh_interval": "daily",
            "config": {
                "metrics": ["otif", "cycle_time", "backorders"],
                "dimensions": ["route", "branch"],
                "tags": ["logistics", "service"],
            },
            "widgets": [
                {
                    "name": "OTIF gauge",
                    "widget_type": "d3-gauge",
                    "layout": {"w": 4, "h": 4},
                    "configuration": {"value_field": "otif", "min": 0, "max": 100},
                },
            ],
        },
        {
            "slug": "pyg_resumen",
            "name": "P&L Snapshot",
            "category": "managerial",
            "description": "Income statement highlights, gross margin and net result.",
            "refresh_interval": "monthly",
            "config": {
                "metrics": ["revenue", "cogs", "gross_margin", "ebitda", "net_income"],
                "dimensions": ["month", "business_unit"],
                "tags": ["financial", "p&l"],
            },
            "widgets": [
                {
                    "name": "Waterfall P&L bridge",
                    "widget_type": "d3-waterfall",
                    "layout": {"w": 6, "h": 4},
                    "configuration": {"sequence": ["revenue", "cogs", "gross_margin", "operating_expenses", "ebitda", "net_income"]},
                },
            ],
        },
        {
            "slug": "pyg_bridge",
            "name": "Revenue to Net Income Bridge",
            "category": "managerial",
            "description": "Bridge view highlighting impact of expenses and profits.",
            "refresh_interval": "monthly",
            "config": {
                "metrics": ["revenue", "gross_margin", "ebitda", "net_income"],
                "dimensions": ["month"],
                "tags": ["financial", "bridge"],
            },
            "widgets": [
                {
                    "name": "Bridge chart",
                    "widget_type": "d3-waterfall",
                    "layout": {"w": 6, "h": 4},
                    "configuration": {"sequence": ["revenue", "cogs", "opex", "ebitda", "depreciation", "net_income"]},
                },
            ],
        },
        {
            "slug": "ebitda_trend",
            "name": "EBITDA Trend",
            "category": "managerial",
            "description": "EBITDA evolution and variance vs budget.",
            "refresh_interval": "monthly",
            "config": {
                "metrics": ["ebitda", "budget", "variance"],
                "dimensions": ["month", "business_unit"],
                "tags": ["financial", "ebitda"],
            },
            "widgets": [
                {
                    "name": "EBITDA trend line",
                    "widget_type": "d3-line",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "month", "y_field": "ebitda", "comparison_field": "budget"},
                },
            ],
        },
        {
            "slug": "liquidez_solvencia",
            "name": "Liquidity & Solvency",
            "category": "managerial",
            "description": "Liquidity ratios, debt to equity and quick ratio status.",
            "refresh_interval": "monthly",
            "config": {
                "metrics": ["current_ratio", "quick_ratio", "debt_to_equity"],
                "dimensions": ["month"],
                "tags": ["financial", "liquidity"],
            },
            "widgets": [
                {
                    "name": "Liquidity scorecards",
                    "widget_type": "d3-cards",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"metrics": ["current_ratio", "quick_ratio", "debt_to_equity"]},
                },
            ],
        },
        {
            "slug": "endeudamiento_cobertura",
            "name": "Debt & Interest Coverage",
            "category": "managerial",
            "description": "Debt ratios and interest coverage indicator.",
            "refresh_interval": "monthly",
            "config": {
                "metrics": ["total_debt", "interest_expense", "interest_coverage"],
                "dimensions": ["month"],
                "tags": ["financial", "debt"],
            },
            "widgets": [
                {
                    "name": "Coverage bar chart",
                    "widget_type": "d3-bar",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "month", "y_field": "interest_coverage"},
                },
            ],
        },
        {
            "slug": "ccc_ciclo_efectivo",
            "name": "Cash Conversion Cycle",
            "category": "managerial",
            "description": "DSO, DIO, DPO and resulting cash conversion cycle.",
            "refresh_interval": "weekly",
            "config": {
                "metrics": ["dso", "dio", "dpo", "ccc"],
                "dimensions": ["month", "business_unit"],
                "tags": ["financial", "working_capital"],
            },
            "widgets": [
                {
                    "name": "CCC stacked area",
                    "widget_type": "d3-area",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "month", "y_fields": ["dso", "dio", "dpo"]},
                },
            ],
        },
        {
            "slug": "cash_flow_waterfall",
            "name": "Cash Flow Waterfall",
            "category": "managerial",
            "description": "Operating, investing and financing flows with period variance.",
            "refresh_interval": "monthly",
            "config": {
                "metrics": ["operating_flow", "investing_flow", "financing_flow", "cash_variation"],
                "dimensions": ["month"],
                "tags": ["financial", "cashflow"],
            },
            "widgets": [
                {
                    "name": "Cash flow waterfall",
                    "widget_type": "d3-waterfall",
                    "layout": {"w": 6, "h": 4},
                    "configuration": {"sequence": ["operating_flow", "investing_flow", "financing_flow", "cash_variation"]},
                },
            ],
        },
        {
            "slug": "burn_runway",
            "name": "Burn Rate & Runway",
            "category": "managerial",
            "description": "Monthly burn rate and runway indicator using current cash.",
            "refresh_interval": "weekly",
            "config": {
                "metrics": ["burn_rate", "runway_months", "cash_balance"],
                "dimensions": ["month"],
                "tags": ["financial", "cashflow"],
            },
            "widgets": [
                {
                    "name": "Runway gauge",
                    "widget_type": "d3-gauge",
                    "layout": {"w": 4, "h": 4},
                    "configuration": {"value_field": "runway_months", "min": 0, "max": 24},
                },
            ],
        },
        {
            "slug": "presupuesto_vs_real",
            "name": "Budget vs Actuals",
            "category": "managerial",
            "description": "Budget vs actual variance with absolute and percentage deviation.",
            "refresh_interval": "monthly",
            "config": {
                "metrics": ["budget", "actual", "variance_abs", "variance_pct"],
                "dimensions": ["account", "month"],
                "tags": ["financial", "budget"],
            },
            "widgets": [
                {
                    "name": "Variance lollipop",
                    "widget_type": "d3-lollipop",
                    "layout": {"w": 6, "h": 3},
                    "configuration": {"x_field": "account", "y_field": "variance_pct"},
                },
            ],
        },
    ]

    for definition in definitions:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=definition["slug"],
            empresa=None,
            defaults={
                "name": definition["name"],
                "description": definition["description"],
                "category": definition["category"],
                "config": definition["config"],
                "metadata": {
                    "created_by": "system",
                    "seeded_at": now.isoformat(),
                    "tags": definition["config"].get("tags", []),
                },
                "refresh_interval": definition["refresh_interval"],
                "is_active": True,
            },
        )

        ReportWidget.objects.filter(report=report_def).delete()
        for idx, widget in enumerate(definition.get("widgets", []), start=1):
            ReportWidget.objects.create(
                report=report_def,
                name=widget["name"],
                widget_type=widget["widget_type"],
                order=idx,
                layout=widget.get("layout", {}),
                configuration=widget.get("configuration", {}),
            )


def delete_report_definitions(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    slugs = [
        "ventas_resumen",
        "ventas_mix_canal",
        "ventas_ticket_medio",
        "clientes_churn_ltv",
        "inventario_rotacion_cobertura",
        "compras_cumplimiento",
        "ar_aging_dso",
        "ap_aging_dpo",
        "logistica_otif",
        "pyg_resumen",
        "pyg_bridge",
        "ebitda_trend",
        "liquidez_solvencia",
        "endeudamiento_cobertura",
        "ccc_ciclo_efectivo",
        "cash_flow_waterfall",
        "burn_runway",
        "presupuesto_vs_real",
    ]
    ReportDefinition.objects.filter(slug__in=slugs, empresa__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_report_definitions, delete_report_definitions),
    ]


