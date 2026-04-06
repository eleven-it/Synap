# Metadatos de sección «Informes Legacy» + placeholders de catálogo mayoristapp
from django.db import migrations
from django.utils import timezone

_LEGACY_META_SLUGS = (
    "pedidos-pendientes",
    "remitos-no-facturados",
    "remitos_no_facturados",
    "uninvoiced_remitos",
    "cash_flow_detailed_movements",
    "cash_flow_by_account",
    "ventas_netas",
    "sales_summary",
    "total-consolidado-operativo",
    "inventario_rotacion_cobertura",
    "clientes_churn_ltv",
)


def _merge_metadata(report, patch: dict) -> None:
    meta = dict(report.metadata or {})
    meta.update(patch)
    report.metadata = meta


def seed_catalog_legacy_metadata(apps, schema_editor):
    """Asigna catalog_legacy_section y catalog_legacy_order en metadata para el catálogo."""
    ReportDefinition = apps.get_model("reports", "ReportDefinition")

    patches = {
        "pedidos-pendientes": {"catalog_legacy_section": "comprobantes", "catalog_legacy_order": 10},
        "remitos-no-facturados": {"catalog_legacy_section": "comprobantes", "catalog_legacy_order": 20},
        "remitos_no_facturados": {"catalog_legacy_section": "comprobantes", "catalog_legacy_order": 20},
        "uninvoiced_remitos": {"catalog_legacy_section": "comprobantes", "catalog_legacy_order": 30},
        "cash_flow_detailed_movements": {"catalog_legacy_section": "comprobantes", "catalog_legacy_order": 40},
        "cash_flow_by_account": {"catalog_legacy_section": "comprobantes", "catalog_legacy_order": 50},
        "ventas_netas": {"catalog_legacy_section": "listados", "catalog_legacy_order": 10},
        "sales_summary": {"catalog_legacy_section": "listados", "catalog_legacy_order": 20},
        "total-consolidado-operativo": {"catalog_legacy_section": "listados", "catalog_legacy_order": 30},
        "inventario_rotacion_cobertura": {"catalog_legacy_section": "listados", "catalog_legacy_order": 40},
        "clientes_churn_ltv": {"catalog_legacy_section": "listados", "catalog_legacy_order": 50},
    }

    for slug, patch in patches.items():
        row = ReportDefinition.objects.filter(slug=slug, empresa__isnull=True).first()
        if row:
            _merge_metadata(row, patch)
            row.save(update_fields=["metadata"])


def create_mayoristapp_placeholder_reports(apps, schema_editor):
    """Entradas de catálogo visibles hasta conectar query_runner / relays."""
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    ReportWidget = apps.get_model("reports", "ReportWidget")
    now = timezone.now()

    specs = [
        {
            "slug": "mayoristapp-devoluciones",
            "name": "Devoluciones (legacy)",
            "description": "Listado de devoluciones alineado a mayoristapp. Vista previa en catálogo; datos legacy al conectar el relay.",
            "section": "listados",
            "order": 60,
            "tags": ["mayoristapp", "legacy", "listados", "catalog_preview"],
        },
        {
            "slug": "mayoristapp-filtros-estadisticas",
            "name": "Filtros para estadísticas (legacy)",
            "description": "Opciones de filtro para informes estadísticos. Vista previa en catálogo; datos legacy al conectar el relay.",
            "section": "listados",
            "order": 70,
            "tags": ["mayoristapp", "legacy", "listados", "catalog_preview"],
        },
        {
            "slug": "mayoristapp-comprobantes-no-cancelados",
            "name": "Comprobantes no cancelados (legacy)",
            "description": "Listado de comprobantes no anulados. Vista previa en catálogo; datos legacy al conectar el relay.",
            "section": "comprobantes",
            "order": 55,
            "tags": ["mayoristapp", "legacy", "comprobantes", "catalog_preview"],
        },
    ]

    for spec in specs:
        report_def, _ = ReportDefinition.objects.update_or_create(
            slug=spec["slug"],
            empresa=None,
            defaults={
                "name": spec["name"],
                "description": spec["description"],
                "category": "operational",
                "config": {
                    "metrics": ["lineas"],
                    "dimensions": ["estado", "detalle"],
                    "tags": spec["tags"],
                    "notes": ["Placeholder de catálogo: muestra datos de muestra hasta integrar motor legacy."],
                },
                "metadata": {
                    "created_by": "system",
                    "seeded_at": now.isoformat(),
                    "catalog_legacy_section": spec["section"],
                    "catalog_legacy_order": spec["order"],
                    "mayoristapp_placeholder": True,
                },
                "refresh_interval": "daily",
                "is_active": True,
            },
        )

        ReportWidget.objects.filter(report=report_def).delete()
        ReportWidget.objects.create(
            report=report_def,
            name="Tabla (vista previa)",
            widget_type="pivot-table",
            order=1,
            layout={"w": 12, "h": 8},
            configuration={
                "rows": ["estado", "detalle"],
                "columns": [],
                "values": ["lineas"],
                "aggregation": "sum",
                "pagination": False,
                "sortable": True,
                "filterable": False,
                "exportable": False,
            },
        )


def reverse_seed_metadata(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    keys = ("catalog_legacy_section", "catalog_legacy_order")
    for slug in _LEGACY_META_SLUGS:
        row = ReportDefinition.objects.filter(slug=slug, empresa__isnull=True).first()
        if not row:
            continue
        meta = dict(row.metadata or {})
        changed = False
        for k in keys:
            if k in meta:
                del meta[k]
                changed = True
        if changed:
            row.metadata = meta
            row.save(update_fields=["metadata"])


def reverse_placeholders(apps, schema_editor):
    ReportDefinition = apps.get_model("reports", "ReportDefinition")
    for slug in (
        "mayoristapp-devoluciones",
        "mayoristapp-filtros-estadisticas",
        "mayoristapp-comprobantes-no-cancelados",
    ):
        ReportDefinition.objects.filter(slug=slug, empresa__isnull=True).delete()


def forward(apps, schema_editor):
    seed_catalog_legacy_metadata(apps, schema_editor)
    create_mayoristapp_placeholder_reports(apps, schema_editor)


def backward(apps, schema_editor):
    reverse_placeholders(apps, schema_editor)
    reverse_seed_metadata(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0030_add_total_consolidado_operativo"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
