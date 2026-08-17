# Almacén PostgreSQL historial Monthly Reporting licenciatarios.
from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def seed_monthly_reporting_packs(apps, schema_editor):
    from reports.services.monthly_reporting_pack_seed import seed_monthly_reporting_packs as _seed

    MonthlyReportingPack = apps.get_model("reports", "MonthlyReportingPack")
    _seed(MonthlyReportingPack)


def unseed_monthly_reporting_packs(apps, schema_editor):
    MonthlyReportingPack = apps.get_model("reports", "MonthlyReportingPack")
    MonthlyReportingPack.objects.filter(
        pack_id__in=[
            "levis_bw",
            "levis_lw_dz",
            "levis_lw_pk",
            "lw_propia",
            "puma_bw",
            "puma_sw",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0039_add_ventas_mensuales_licenciatarios_report"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonthlyReportingPack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pack_id", models.SlugField(max_length=32, unique=True, verbose_name="Pack ID")),
                ("codigo_salida", models.CharField(max_length=8, verbose_name="Código salida")),
                ("marca_anet", models.CharField(max_length=8, verbose_name="Marca AdministraNET")),
                ("product_group", models.CharField(max_length=64, verbose_name="Product group")),
                (
                    "template_family",
                    models.CharField(
                        choices=[("levis", "Levi's"), ("lw", "LW propia"), ("puma", "Puma")],
                        max_length=16,
                        verbose_name="Familia plantilla",
                    ),
                ),
                (
                    "unit_mode",
                    models.CharField(
                        choices=[("dozens", "Docenas"), ("packs", "Packs")],
                        max_length=16,
                        verbose_name="Modo unidad",
                    ),
                ),
                ("royalty_rate", models.DecimalField(decimal_places=6, max_digits=7, verbose_name="Tasa regalía")),
                ("config_version", models.PositiveIntegerField(default=1, verbose_name="Versión config")),
                ("active", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado")),
            ],
            options={
                "verbose_name": "Pack Monthly Reporting",
                "verbose_name_plural": "Packs Monthly Reporting",
                "ordering": ("pack_id",),
            },
        ),
        migrations.CreateModel(
            name="MonthlyReportingClientMatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("seed_key", models.CharField(max_length=128, unique=True, verbose_name="Clave seed")),
                ("seed_customer_code", models.CharField(blank=True, default="", max_length=64, verbose_name="Código cliente seed")),
                ("seed_customer_name", models.CharField(max_length=255, verbose_name="Nombre cliente seed")),
                ("seed_city", models.CharField(blank=True, default="", max_length=128, verbose_name="Ciudad")),
                ("seed_store_type", models.CharField(blank=True, default="", max_length=128, verbose_name="Tipo tienda")),
                ("seed_product_group", models.CharField(blank=True, default="", max_length=128, verbose_name="Product group seed")),
                ("seed_uf", models.CharField(blank=True, default="", max_length=64, verbose_name="UF")),
                ("base_empresa", models.CharField(blank=True, default="", max_length=128, verbose_name="Base empresa")),
                ("anet_cliente_id", models.PositiveIntegerField(blank=True, null=True, verbose_name="ID cliente AdministraNET")),
                (
                    "estado",
                    models.CharField(
                        choices=[("pending", "Pendiente"), ("matched", "Matcheado")],
                        default="pending",
                        max_length=16,
                        verbose_name="Estado",
                    ),
                ),
                ("actor_id_usuario", models.PositiveIntegerField(blank=True, null=True)),
                ("actor_cod_usuario", models.CharField(blank=True, default="", max_length=64)),
                ("actor_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Match cliente Monthly Reporting",
                "verbose_name_plural": "Matches clientes Monthly Reporting",
            },
        ),
        migrations.CreateModel(
            name="MonthlyReportingSuperArtCatalogVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField(verbose_name="Versión")),
                ("source_hash", models.CharField(blank=True, default="", max_length=64)),
                ("source_label", models.CharField(blank=True, default="", max_length=255)),
                (
                    "estado",
                    models.CharField(
                        choices=[("draft", "Borrador"), ("active", "Activa"), ("archived", "Archivada")],
                        default="draft",
                        max_length=16,
                        verbose_name="Estado",
                    ),
                ),
                ("actor_id_usuario", models.PositiveIntegerField(blank=True, null=True)),
                ("actor_cod_usuario", models.CharField(blank=True, default="", max_length=64)),
                ("actor_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Versión catálogo SuperArt",
                "verbose_name_plural": "Versiones catálogo SuperArt",
            },
        ),
        migrations.CreateModel(
            name="MonthlyReportingImportBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file_name", models.CharField(max_length=255, verbose_name="Nombre archivo")),
                ("file_size", models.PositiveBigIntegerField(default=0, verbose_name="Tamaño bytes")),
                ("file_format", models.CharField(max_length=8, verbose_name="Formato")),
                ("file_sha256", models.CharField(max_length=64, verbose_name="SHA-256")),
                ("replace_mode", models.BooleanField(default=False, verbose_name="Modo reemplazo")),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pending", "Pendiente"),
                            ("applied", "Aplicado"),
                            ("failed", "Fallido"),
                            ("duplicate", "Duplicado"),
                        ],
                        default="pending",
                        max_length=16,
                        verbose_name="Estado",
                    ),
                ),
                ("rows_created", models.PositiveIntegerField(default=0, verbose_name="Filas creadas")),
                ("rows_updated", models.PositiveIntegerField(default=0, verbose_name="Filas actualizadas")),
                ("rows_skipped", models.PositiveIntegerField(default=0, verbose_name="Filas omitidas")),
                ("error_message", models.TextField(blank=True, default="", verbose_name="Error")),
                ("actor_id_usuario", models.PositiveIntegerField(blank=True, null=True, verbose_name="ID usuario legacy")),
                ("actor_cod_usuario", models.CharField(blank=True, default="", max_length=64, verbose_name="Código usuario")),
                ("actor_nombre", models.CharField(blank=True, default="", max_length=255, verbose_name="Nombre actor")),
                ("audit_json", models.JSONField(blank=True, default=dict, verbose_name="Auditoría")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creado")),
                ("applied_at", models.DateTimeField(blank=True, null=True, verbose_name="Aplicado")),
                (
                    "duplicate_of",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="duplicates",
                        to="reports.monthlyreportingimportbatch",
                        verbose_name="Duplicado de",
                    ),
                ),
                (
                    "pack",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="import_batches",
                        to="reports.monthlyreportingpack",
                        verbose_name="Pack",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lote importación Monthly Reporting",
                "verbose_name_plural": "Lotes importación Monthly Reporting",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="MonthlyReportingClientMatchAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("before_json", models.JSONField(blank=True, default=dict, verbose_name="Antes")),
                ("after_json", models.JSONField(blank=True, default=dict, verbose_name="Después")),
                ("actor_id_usuario", models.PositiveIntegerField(blank=True, null=True)),
                ("actor_cod_usuario", models.CharField(blank=True, default="", max_length=64)),
                ("actor_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Fecha")),
                (
                    "match",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audits",
                        to="reports.monthlyreportingclientmatch",
                        verbose_name="Match",
                    ),
                ),
            ],
            options={
                "verbose_name": "Auditoría match Monthly Reporting",
                "verbose_name_plural": "Auditorías match Monthly Reporting",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="MonthlyReportingSeedRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField(verbose_name="Mes (día 1)")),
                ("units", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=20)),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=20)),
                ("units_men", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=20)),
                ("units_women", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=20)),
                ("amount_men", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=20)),
                ("amount_women", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=20)),
                ("city", models.CharField(blank=True, default="", max_length=128)),
                ("store_type", models.CharField(blank=True, default="", max_length=128)),
                ("uf", models.CharField(blank=True, default="", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seed_rows",
                        to="reports.monthlyreportingimportbatch",
                        verbose_name="Lote",
                    ),
                ),
                (
                    "match",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seed_rows",
                        to="reports.monthlyreportingclientmatch",
                        verbose_name="Match cliente",
                    ),
                ),
                (
                    "pack",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seed_rows",
                        to="reports.monthlyreportingpack",
                        verbose_name="Pack",
                    ),
                ),
            ],
            options={
                "verbose_name": "Fila seed Monthly Reporting",
                "verbose_name_plural": "Filas seed Monthly Reporting",
            },
        ),
        migrations.CreateModel(
            name="MonthlyReportingSuperArtCatalogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("superart", models.CharField(max_length=64, verbose_name="SuperArt")),
                (
                    "genero",
                    models.CharField(
                        choices=[("men", "Men"), ("women", "Women")],
                        max_length=8,
                        verbose_name="Género",
                    ),
                ),
                (
                    "version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="reports.monthlyreportingsuperartcatalogversion",
                        verbose_name="Versión",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entrada catálogo SuperArt",
                "verbose_name_plural": "Entradas catálogo SuperArt",
            },
        ),
        migrations.CreateModel(
            name="MonthlyReportingSuperArtQAPending",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("superart", models.CharField(max_length=64, unique=True, verbose_name="SuperArt")),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("occurrence_count", models.PositiveIntegerField(default=1)),
                ("sample_json", models.JSONField(blank=True, default=dict)),
                (
                    "resolved_version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resolved_qa",
                        to="reports.monthlyreportingsuperartcatalogversion",
                        verbose_name="Versión resolución",
                    ),
                ),
            ],
            options={
                "verbose_name": "SuperArt QA pendiente",
                "verbose_name_plural": "SuperArt QA pendientes",
            },
        ),
        migrations.AddConstraint(
            model_name="monthlyreportingclientmatch",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("estado", "matched"),
                    ("anet_cliente_id__isnull", False),
                )
                | models.Q(
                    ("estado", "pending"),
                    ("anet_cliente_id__isnull", True),
                ),
                name="reports_mr_match_estado_anet_chk",
            ),
        ),
        migrations.AddIndex(
            model_name="monthlyreportingclientmatch",
            index=models.Index(fields=["estado"], name="reports_mr_match_estado_idx"),
        ),
        migrations.AddConstraint(
            model_name="monthlyreportingimportbatch",
            constraint=models.UniqueConstraint(
                condition=models.Q(("duplicate_of__isnull", True), ("estado", "applied")),
                fields=("pack", "file_sha256"),
                name="reports_mr_batch_pack_sha_applied_uq",
            ),
        ),
        migrations.AddIndex(
            model_name="monthlyreportingimportbatch",
            index=models.Index(fields=["pack", "file_sha256"], name="reports_mr_batch_sha_idx"),
        ),
        migrations.AddIndex(
            model_name="monthlyreportingimportbatch",
            index=models.Index(fields=["estado"], name="reports_mr_batch_estado_idx"),
        ),
        migrations.AddConstraint(
            model_name="monthlyreportingseedrow",
            constraint=models.UniqueConstraint(
                fields=("pack", "match", "month"),
                name="reports_mr_seed_pack_match_month_uq",
            ),
        ),
        migrations.AddIndex(
            model_name="monthlyreportingseedrow",
            index=models.Index(fields=["pack", "month"], name="reports_mr_seed_pack_month_idx"),
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE reports_monthlyreportingseedrow "
                "ADD CONSTRAINT reports_mr_seed_month_first_day_chk "
                "CHECK (EXTRACT(DAY FROM month) = 1);"
            ),
            reverse_sql=(
                "ALTER TABLE reports_monthlyreportingseedrow "
                "DROP CONSTRAINT IF EXISTS reports_mr_seed_month_first_day_chk;"
            ),
        ),
        migrations.AddConstraint(
            model_name="monthlyreportingsuperartcatalogversion",
            constraint=models.UniqueConstraint(fields=("version",), name="reports_mr_superart_version_uq"),
        ),
        migrations.AddConstraint(
            model_name="monthlyreportingsuperartcatalogversion",
            constraint=models.UniqueConstraint(
                condition=models.Q(("estado", "active")),
                fields=("estado",),
                name="reports_mr_superart_active_uq",
            ),
        ),
        migrations.AddConstraint(
            model_name="monthlyreportingsuperartcatalogentry",
            constraint=models.UniqueConstraint(
                fields=("version", "superart"),
                name="reports_mr_superart_entry_uq",
            ),
        ),
        migrations.RunPython(seed_monthly_reporting_packs, unseed_monthly_reporting_packs),
    ]
