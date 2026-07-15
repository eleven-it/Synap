# Mapeo tejedor BEST (TTNOTE) ↔ sue_abm_empleado.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0021_best_deposito_stock_maps"),
    ]

    operations = [
        migrations.CreateModel(
            name="BestOperarioMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("best_codigo", models.CharField(db_index=True, help_text="Letra/código TTNOTE", max_length=16)),
                ("best_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("movimientos_n", models.PositiveIntegerField(default=0)),
                ("admin_id_operario", models.IntegerField(blank=True, db_index=True, null=True)),
                ("admin_nombre", models.CharField(blank=True, default="", max_length=255)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("INFERIDO", "Inferido"),
                            ("AMBIGUO", "Ambiguo"),
                            ("VALIDADO", "Validado"),
                            ("DESCARTADO", "Descartado"),
                            ("SIN_CANDIDATO", "Sin candidato"),
                        ],
                        db_index=True,
                        default="PENDIENTE",
                        max_length=24,
                    ),
                ),
                ("score", models.IntegerField(blank=True, null=True)),
                ("razon", models.CharField(blank=True, default="", max_length=512)),
                ("alt1_id_operario", models.IntegerField(blank=True, null=True)),
                ("alt1_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("requerido_migracion", models.BooleanField(db_index=True, default=True)),
                ("en_snapshot_abierto", models.BooleanField(db_index=True, default=True)),
                (
                    "origen_requerimiento",
                    models.CharField(
                        choices=[
                            ("REPORTE", "Reportes / histórico"),
                            ("CATALOGO", "Catálogo BEST"),
                        ],
                        default="REPORTE",
                        max_length=24,
                    ),
                ),
                ("validado", models.BooleanField(default=False)),
                ("validado_por", models.CharField(blank=True, default="", max_length=64)),
                ("validado_en", models.DateTimeField(blank=True, null=True)),
                ("notas", models.TextField(blank=True, default="")),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Mapeo operario/tejedor BEST",
                "verbose_name_plural": "Mapeos operarios/tejedores BEST",
                "db_table": "mpr_best_operario_map",
                "indexes": [
                    models.Index(fields=["base_empresa", "estado"], name="mpr_best_op_base_em_estado_idx"),
                    models.Index(fields=["base_empresa", "validado"], name="mpr_best_op_base_em_valid_idx"),
                ],
                "unique_together": {("base_empresa", "best_codigo")},
            },
        ),
    ]
