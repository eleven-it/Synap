# Guardar conocimiento: trazabilidad de mensaje -> chunk

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="copilotmessage",
            name="saved_to_knowledge",
            field=models.BooleanField(default=False, verbose_name="Guardado como conocimiento"),
        ),
        migrations.AddField(
            model_name="copilotmessage",
            name="knowledge_chunk_id",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="ID del chunk creado (referencia a support_knowledge_chunk)",
            ),
        ),
    ]
