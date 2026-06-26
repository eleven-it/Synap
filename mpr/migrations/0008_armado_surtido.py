# Generated manually for armado surtido MVP

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0007_delete_mprconfig"),
    ]

    operations = [
        migrations.CreateModel(
            name="MprArticuloArmadoSurtido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("id_articulo", models.IntegerField()),
                ("activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Pack habilitado armado surtido",
                "verbose_name_plural": "Packs habilitados armado surtido",
                "ordering": ["base_empresa", "id_articulo"],
            },
        ),
        migrations.CreateModel(
            name="MprArmadoSurtidoMovimiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("codigo_movimiento", models.IntegerField(db_index=True)),
                ("id_articulo_pack", models.IntegerField()),
                ("cantidad_packs", models.IntegerField()),
                ("deposito_origen", models.IntegerField()),
                ("deposito_destino", models.IntegerField()),
                ("id_lista_produccion", models.IntegerField(blank=True, null=True)),
                ("id_operario", models.IntegerField(blank=True, null=True)),
                ("id_usuario", models.IntegerField()),
                ("detalle", models.CharField(blank=True, default="", max_length=500)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Movimiento armado surtido",
                "verbose_name_plural": "Movimientos armado surtido",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.CreateModel(
            name="MprArmadoSurtidoLinea",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("id_articulo_componente", models.IntegerField()),
                ("codigo_articulo", models.CharField(blank=True, default="-", max_length=64)),
                ("descripcion_articulo", models.CharField(blank=True, default="-", max_length=255)),
                ("cantidad_por_pack", models.IntegerField()),
                ("cantidad_total", models.IntegerField()),
                (
                    "movimiento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="mpr.mprarmadosurtidomovimiento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Línea composición armado surtido",
                "verbose_name_plural": "Líneas composición armado surtido",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="mprarticuloarmadosurtido",
            constraint=models.UniqueConstraint(
                fields=("base_empresa", "id_articulo"),
                name="mpr_art_armado_surtido_empresa_art",
            ),
        ),
        migrations.AddIndex(
            model_name="mprarmadosurtidomovimiento",
            index=models.Index(fields=["base_empresa", "codigo_movimiento"], name="mpr_as_mov_be_cod"),
        ),
    ]
