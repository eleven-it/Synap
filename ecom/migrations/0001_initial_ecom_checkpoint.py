# Generated manually for ecom.EcomMigrationCheckpoint

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EcomMigrationCheckpoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module_slug", models.SlugField(db_index=True, max_length=64, unique=True, verbose_name="módulo")),
                ("notes", models.TextField(blank=True, verbose_name="notas")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
            ],
            options={
                "verbose_name": "checkpoint de migración e-com",
                "verbose_name_plural": "checkpoints de migración e-com",
                "ordering": ["-updated_at"],
            },
        ),
    ]
