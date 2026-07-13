# Generated manually for BEST → MPR parity models (PostgreSQL Synap).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0017_bloqueo_fabricando_default_true"),
    ]

    operations = [
        migrations.CreateModel(
            name="BestArticuloMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("best_id_articulo", models.CharField(db_index=True, max_length=32)),
                ("best_codigo", models.CharField(blank=True, default="", max_length=64)),
                ("best_articulo", models.CharField(blank=True, default="", max_length=255)),
                ("best_marca", models.CharField(blank=True, default="", max_length=64)),
                ("best_modelos", models.CharField(blank=True, default="", max_length=128)),
                ("best_colores", models.CharField(blank=True, default="", max_length=64)),
                ("best_color_mode", models.CharField(blank=True, default="", max_length=16)),
                ("best_talle", models.CharField(blank=True, default="", max_length=8)),
                ("best_pack", models.CharField(blank=True, default="", max_length=8)),
                ("best_variant_codes", models.CharField(blank=True, default="", max_length=128)),
                ("admin_idart", models.IntegerField(blank=True, db_index=True, null=True)),
                ("admin_id_manual", models.CharField(blank=True, default="", max_length=64)),
                ("admin_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("admin_cod_art_prov", models.CharField(blank=True, default="", max_length=128)),
                ("admin_pack", models.CharField(blank=True, default="", max_length=8)),
                ("admin_talle", models.CharField(blank=True, default="", max_length=8)),
                ("admin_color_mode", models.CharField(blank=True, default="", max_length=16)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("INFERIDO_ALTO", "Inferido alto"),
                            ("INFERIDO_MEDIO", "Inferido medio"),
                            ("INFERIDO_BAJO", "Inferido bajo"),
                            ("AMBIGUO", "Ambiguo"),
                            ("SIN_CANDIDATO", "Sin candidato"),
                            ("SIN_MATCH", "Sin match confiable"),
                            ("CONFLICTO_1_A_N", "Conflicto 1→N"),
                            ("VALIDADO", "Validado"),
                            ("DESCARTADO", "Descartado (fuera de alcance)"),
                        ],
                        db_index=True,
                        max_length=24,
                    ),
                ),
                ("score", models.IntegerField(blank=True, null=True)),
                ("razon", models.CharField(blank=True, default="", max_length=512)),
                ("candidatos_n", models.PositiveIntegerField(default=0)),
                ("alt1_idart", models.IntegerField(blank=True, null=True)),
                ("alt1_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("alt1_score", models.IntegerField(blank=True, null=True)),
                ("alt2_idart", models.IntegerField(blank=True, null=True)),
                ("alt2_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("alt2_score", models.IntegerField(blank=True, null=True)),
                ("dict_version", models.CharField(blank=True, default="", max_length=32)),
                ("validado", models.BooleanField(default=False)),
                ("validado_por", models.CharField(blank=True, default="", max_length=64)),
                ("validado_en", models.DateTimeField(blank=True, null=True)),
                ("notas", models.TextField(blank=True, default="")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Mapeo artículo BEST",
                "verbose_name_plural": "Mapeos artículos BEST",
                "db_table": "mpr_best_articulo_map",
                "indexes": [
                    models.Index(fields=["base_empresa", "estado"], name="mpr_best_ar_base_em_estado_idx"),
                    models.Index(fields=["base_empresa", "validado"], name="mpr_best_ar_base_em_valid_idx"),
                ],
                "unique_together": {("base_empresa", "best_id_articulo")},
            },
        ),
        migrations.CreateModel(
            name="BestClienteMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("best_cliente", models.CharField(max_length=255)),
                ("best_cuit", models.CharField(blank=True, default="", max_length=32)),
                ("admin_codigo", models.IntegerField(blank=True, null=True)),
                ("admin_nombre", models.CharField(blank=True, default="", max_length=255)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("INFERIDO", "Inferido"),
                            ("AMBIGUO", "Ambiguo"),
                            ("SIN_CANDIDATO", "Sin candidato"),
                            ("VALIDADO", "Validado"),
                            ("DESCARTADO", "Descartado"),
                        ],
                        default="PENDIENTE",
                        max_length=24,
                    ),
                ),
                ("ordenes_abiertas", models.PositiveIntegerField(default=0)),
                ("validado", models.BooleanField(default=False)),
                ("validado_por", models.CharField(blank=True, default="", max_length=64)),
                ("validado_en", models.DateTimeField(blank=True, null=True)),
                ("notas", models.TextField(blank=True, default="")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Mapeo cliente BEST",
                "verbose_name_plural": "Mapeos clientes BEST",
                "db_table": "mpr_best_cliente_map",
                "unique_together": {("base_empresa", "best_cliente", "best_cuit")},
            },
        ),
        migrations.CreateModel(
            name="BestMigrationParity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64, unique=True)),
                ("articulos_total", models.PositiveIntegerField(default=0)),
                ("articulos_resueltos", models.PositiveIntegerField(default=0)),
                ("articulos_ok", models.BooleanField(default=False)),
                ("clientes_total", models.PositiveIntegerField(default=0)),
                ("clientes_resueltos", models.PositiveIntegerField(default=0)),
                ("clientes_ok", models.BooleanField(default=False)),
                (
                    "unidades_ok",
                    models.BooleanField(default=False, help_text="Confirmación manual: cantidades en pares."),
                ),
                ("depositos_ok", models.BooleanField(default=False)),
                ("stock_inicial_ok", models.BooleanField(default=False)),
                ("operarios_ok", models.BooleanField(default=False)),
                ("migracion_habilitada", models.BooleanField(default=False)),
                ("ultimo_recalculo_articulos", models.DateTimeField(blank=True, null=True)),
                ("ultimo_error", models.CharField(blank=True, default="", max_length=500)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Paridad migración BEST",
                "verbose_name_plural": "Paridades migración BEST",
                "db_table": "mpr_best_migration_parity",
            },
        ),
    ]
