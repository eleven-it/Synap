from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mpr", "0014_mprenvio_produccion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mprpartelinea",
            name="id_articulo",
            field=models.IntegerField(
                help_text="ID artículo nivel COMPONENTE (desde grilla Fabricando, E8).",
            ),
        ),
    ]
