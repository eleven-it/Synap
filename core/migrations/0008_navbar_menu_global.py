# Generated manually for NavbarMenuGlobal (visibilidad navbar supervisor)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_increase_permiso_codigo_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="NavbarMenuGlobal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "ocultar_todos_items",
                    models.BooleanField(
                        default=False,
                        help_text="Si está activo, la barra superior no lista módulos (Stock, MPR, etc.) para usuarios que no sean supervisor. El usuario supervisor sigue viendo Archivo.",
                        verbose_name="Ocultar todos los ítems del menú navbar",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Última actualización")),
            ],
            options={
                "verbose_name": "Visibilidad global del menú navbar",
                "verbose_name_plural": "Visibilidad global del menú navbar",
            },
        ),
    ]
