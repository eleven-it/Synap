# Depósitos / etapas y stock inicial BEST → MPR.

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0020_best_requerido_migracion"),
    ]

    operations = [
        migrations.CreateModel(
            name="BestDepositoMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("best_id_deposito", models.IntegerField(db_index=True)),
                ("best_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("tipo_mpr_esperado", models.CharField(blank=True, default="", max_length=32)),
                ("admin_cod_deposito", models.IntegerField(blank=True, db_index=True, null=True)),
                ("admin_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("admin_tipo_mpr", models.CharField(blank=True, default="", max_length=32)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("INFERIDO", "Inferido"),
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
                ("requerido_migracion", models.BooleanField(db_index=True, default=True)),
                ("en_snapshot_abierto", models.BooleanField(db_index=True, default=True)),
                (
                    "origen_requerimiento",
                    models.CharField(
                        choices=[
                            ("PEDIDO_ABIERTO", "Pedido abierto"),
                            ("STOCK_DEPOSITO", "Saldo en depósito"),
                            ("HISTORICO", "Histórico / fuera de alcance"),
                        ],
                        default="STOCK_DEPOSITO",
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
                "verbose_name": "Mapeo depósito BEST",
                "verbose_name_plural": "Mapeos depósitos BEST",
                "db_table": "mpr_best_deposito_map",
            },
        ),
        migrations.CreateModel(
            name="BestStockInicialMap",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("best_id_articulo", models.CharField(db_index=True, max_length=32)),
                ("best_articulo", models.CharField(blank=True, default="", max_length=255)),
                ("best_id_deposito", models.IntegerField(db_index=True)),
                ("best_deposito_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("best_stock_pares", models.DecimalField(decimal_places=4, default=Decimal("0"), max_digits=18)),
                ("best_docenas", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("admin_idart", models.IntegerField(blank=True, db_index=True, null=True)),
                ("admin_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("admin_cod_deposito", models.IntegerField(blank=True, db_index=True, null=True)),
                ("admin_deposito_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("admin_saldo_actual", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("delta_pares", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("LISTO", "Listo"),
                            ("SIN_MAPEO_ARTICULO", "Sin mapeo artículo"),
                            ("SIN_MAPEO_DEPOSITO", "Sin mapeo depósito"),
                            ("CONCILIADO", "Conciliado"),
                            ("CARGADO", "Cargado"),
                            ("DESCARTADO", "Descartado"),
                        ],
                        db_index=True,
                        default="PENDIENTE",
                        max_length=24,
                    ),
                ),
                ("requerido_migracion", models.BooleanField(db_index=True, default=True)),
                (
                    "origen_requerimiento",
                    models.CharField(
                        choices=[("STOCK_DEPOSITO", "Saldo en depósito")],
                        default="STOCK_DEPOSITO",
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
                "verbose_name": "Stock inicial BEST",
                "verbose_name_plural": "Stock inicial BEST",
                "db_table": "mpr_best_stock_inicial_map",
            },
        ),
        migrations.AddField(
            model_name="bestmigrationparity",
            name="depositos_total",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="bestmigrationparity",
            name="depositos_resueltos",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="bestmigrationparity",
            name="stock_inicial_total",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="bestmigrationparity",
            name="stock_inicial_resueltos",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name="bestdepositomap",
            index=models.Index(fields=["base_empresa", "estado"], name="mpr_best_de_base_em_8a1f2d_idx"),
        ),
        migrations.AddIndex(
            model_name="bestdepositomap",
            index=models.Index(fields=["base_empresa", "validado"], name="mpr_best_de_base_em_9b2c3e_idx"),
        ),
        migrations.AddIndex(
            model_name="beststockinicialmap",
            index=models.Index(fields=["base_empresa", "estado"], name="mpr_best_st_base_em_1d4e5f_idx"),
        ),
        migrations.AddIndex(
            model_name="beststockinicialmap",
            index=models.Index(fields=["base_empresa", "requerido_migracion"], name="mpr_best_st_base_em_2e5f6a_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="bestdepositomap",
            unique_together={("base_empresa", "best_id_deposito")},
        ),
        migrations.AlterUniqueTogether(
            name="beststockinicialmap",
            unique_together={("base_empresa", "best_id_articulo", "best_id_deposito")},
        ),
    ]
