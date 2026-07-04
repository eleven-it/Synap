import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0010_mprrosterdia_mprturno_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MprParte",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "base_empresa",
                    models.CharField(
                        db_index=True,
                        help_text="Scope por empresa.",
                        max_length=64,
                    ),
                ),
                (
                    "fecha_produccion",
                    models.DateField(
                        help_text="Fecha de producción. Puede ser pasada (registro diferido). UI: dd/MM/yyyy.",
                    ),
                ),
                (
                    "id_usuario",
                    models.IntegerField(
                        help_text="Usuario que registró el parte en Synap.",
                    ),
                ),
                ("registrado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "notas",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Notas opcionales del parte.",
                        max_length=500,
                    ),
                ),
                (
                    "turno",
                    models.ForeignKey(
                        help_text="Turno de producción. PROTECT: no eliminar si hay partes.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="partes",
                        to="mpr.mprturno",
                    ),
                ),
            ],
            options={
                "verbose_name": "Parte de producción",
                "verbose_name_plural": "Partes de producción",
                "ordering": ["-registrado_en"],
            },
        ),
        migrations.AddIndex(
            model_name="mprparte",
            index=models.Index(
                fields=["base_empresa", "fecha_produccion"],
                name="mpr_parte_emp_fecha_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="mprparte",
            index=models.Index(
                fields=["base_empresa", "turno_id"],
                name="mpr_parte_emp_turno_idx",
            ),
        ),
        migrations.CreateModel(
            name="MprParteLinea",
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
                    "parte",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="mpr.mprparte",
                    ),
                ),
                (
                    "id_articulo",
                    models.IntegerField(
                        help_text="ID artículo nivel PACK (igual que OPT).",
                    ),
                ),
                (
                    "id_operario",
                    models.IntegerField(
                        help_text="FK lógico a sue_abm_empleado.id_sue_abm_empleado.",
                    ),
                ),
                (
                    "operario_nombre",
                    models.CharField(
                        default="-",
                        help_text="Snapshot de nombre_empleado al momento del registro. No se actualiza.",
                        max_length=255,
                    ),
                ),
                (
                    "cantidad",
                    models.DecimalField(decimal_places=2, max_digits=15),
                ),
            ],
            options={
                "verbose_name": "Línea de parte de producción",
                "verbose_name_plural": "Líneas de parte de producción",
                "ordering": ["id_articulo", "id_operario"],
            },
        ),
        migrations.AddConstraint(
            model_name="mprpartelinea",
            constraint=models.UniqueConstraint(
                fields=("parte", "id_articulo", "id_operario"),
                name="mpr_parte_linea_unico",
            ),
        ),
        migrations.CreateModel(
            name="MprParteAjuste",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "parte",
                    models.ForeignKey(
                        help_text="PROTECT: no eliminar cabecera si existen ajustes.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ajustes",
                        to="mpr.mprparte",
                    ),
                ),
                ("id_articulo", models.IntegerField()),
                ("id_operario", models.IntegerField()),
                (
                    "delta",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Delta positivo o negativo. Cantidad efectiva = linea.cantidad + Σdeltas.",
                        max_digits=15,
                    ),
                ),
                ("motivo", models.CharField(max_length=255)),
                ("id_usuario", models.IntegerField()),
                ("registrado_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Ajuste de parte de producción",
                "verbose_name_plural": "Ajustes de parte de producción",
                "ordering": ["registrado_en"],
            },
        ),
        migrations.AddIndex(
            model_name="mprparteajuste",
            index=models.Index(
                fields=["parte", "id_articulo", "id_operario"],
                name="mpr_parte_ajuste_linea_idx",
            ),
        ),
    ]
