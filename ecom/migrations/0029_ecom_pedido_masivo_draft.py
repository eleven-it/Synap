# Generated manually — borrador pedido masivo por sucursales (Phase 1)

from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0028_ecomcartitem_presentacion"),
    ]

    operations = [
        migrations.CreateModel(
            name="EcomPedidoMasivoDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64, verbose_name="base empresa")),
                ("id_usuario", models.IntegerField(db_index=True, verbose_name="usuario")),
                ("cod_viajante", models.IntegerField(blank=True, null=True, verbose_name="CodViajante")),
                ("id_cliente", models.IntegerField(db_index=True, verbose_name="cliente")),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("borrador", "Borrador"),
                            ("confirmando", "Confirmando"),
                            ("confirmado", "Confirmado"),
                            ("archivado", "Archivado"),
                        ],
                        db_index=True,
                        default="borrador",
                        max_length=16,
                        verbose_name="estado",
                    ),
                ),
                (
                    "ultimo_error",
                    models.JSONField(blank=True, default=dict, verbose_name="último error por sucursal"),
                ),
                (
                    "codigos_movimiento",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Lista de CodigoMovimiento PED creados al confirmar.",
                        verbose_name="CodigoMovimiento del lote",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
            ],
            options={
                "verbose_name": "borrador pedido masivo",
                "verbose_name_plural": "borradores pedido masivo",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="EcomPedidoMasivoDraftCelda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("id_articulo", models.IntegerField(db_index=True, verbose_name="artículo")),
                ("id_cliente_domicilio", models.IntegerField(db_index=True, verbose_name="cliente_domicilio")),
                (
                    "cantidad_packs",
                    models.DecimalField(
                        decimal_places=3,
                        default=Decimal("0"),
                        max_digits=14,
                        verbose_name="cantidad packs",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
                (
                    "draft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="celdas",
                        to="ecom.ecompedidomasivodraft",
                    ),
                ),
            ],
            options={
                "verbose_name": "celda pedido masivo",
                "verbose_name_plural": "celdas pedido masivo",
            },
        ),
        migrations.AddIndex(
            model_name="ecompedidomasivodraft",
            index=models.Index(
                fields=["base_empresa", "id_usuario", "estado"],
                name="ecom_ecompe_base_em_a8f0c1_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ecompedidomasivodraft",
            index=models.Index(
                fields=["base_empresa", "id_cliente", "estado"],
                name="ecom_ecompe_base_em_b1d2e3_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="ecompedidomasivodraftcelda",
            constraint=models.UniqueConstraint(
                fields=("draft", "id_articulo", "id_cliente_domicilio"),
                name="uniq_ecom_masivo_celda_draft_art_dom",
            ),
        ),
    ]
