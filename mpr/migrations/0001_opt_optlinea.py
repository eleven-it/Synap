# Migración MPR: modelos Opt y OptLinea para agrupar OPT con múltiples artículos.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Opt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("base_empresa", models.CharField(db_index=True, max_length=64)),
                ("id_lista_principal", models.BigIntegerField(help_text="Primer id_lista_produccion de la OPT (para enlaces y detalle).")),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("id_usuario", models.IntegerField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "OPT (Pedido de producción)",
                "verbose_name_plural": "OPT (Pedidos de producción)",
                "db_table": "mpr_opt",
                "ordering": ["-fecha_creacion"],
            },
        ),
        migrations.CreateModel(
            name="OptLinea",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("id_lista_produccion", models.BigIntegerField()),
                ("id_articulo", models.IntegerField()),
                ("cantidad_pedida", models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ("opt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lineas", to="mpr.opt")),
            ],
            options={
                "verbose_name": "Línea OPT",
                "verbose_name_plural": "Líneas OPT",
                "db_table": "mpr_opt_linea",
                "ordering": ["id"],
                "unique_together": {("opt", "id_lista_produccion")},
            },
        ),
    ]
