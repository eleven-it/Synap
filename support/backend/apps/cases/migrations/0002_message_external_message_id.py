# Dedupe mensajes entrantes: external_message_id + UNIQUE (channel_type, external_message_id)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="external_message_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=255,
                verbose_name="ID mensaje en el canal (evita duplicados por webhook)",
            ),
        ),
        migrations.AddConstraint(
            model_name="message",
            constraint=models.UniqueConstraint(
                condition=models.Q(external_message_id__gt=""),
                fields=("channel_type", "external_message_id"),
                name="support_message_channel_external_msg_uniq",
            ),
        ),
    ]
