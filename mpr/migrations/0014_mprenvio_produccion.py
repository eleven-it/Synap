from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mpr", "0013_mprparte_id_lista_produccion"),
    ]

    operations = [
        migrations.CreateModel(
            name="MprEnvioProduccion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "base_empresa",
                    models.CharField(
                        db_index=True,
                        help_text="Scope por empresa (base_empresa de AdministraNET).",
                        max_length=64,
                    ),
                ),
                (
                    "id_articulo",
                    models.IntegerField(
                        help_text="ID artículo nivel COMPONENTE (ya explotado, no PACK).",
                    ),
                ),
                (
                    "cantidad",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Cantidad enviada en unidades del componente.",
                        max_digits=15,
                    ),
                ),
                (
                    "id_usuario",
                    models.IntegerField(
                        help_text="ID usuario AdministraNET que realizó el envío.",
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "anulado",
                    models.BooleanField(
                        default=False,
                        help_text="True si el envío fue anulado (solo desde admin Django en E7).",
                    ),
                ),
            ],
            options={
                "verbose_name": "Envío a producción desde tablero",
                "verbose_name_plural": "Envíos a producción desde tablero",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.AddIndex(
            model_name="mprenvioproduccion",
            index=models.Index(
                fields=["base_empresa", "id_articulo"],
                name="mpr_ep_emp_art_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="mprenvioproduccion",
            index=models.Index(
                fields=["base_empresa", "creado_en"],
                name="mpr_ep_emp_fecha_idx",
            ),
        ),
    ]
