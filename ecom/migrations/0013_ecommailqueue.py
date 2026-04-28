from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecom", "0012_update_checkpoint_comprobantes_no_cancelados"),
    ]

    operations = [
        migrations.CreateModel(
            name="EcomMailQueue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="actualizado")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "pendiente"), ("sent", "enviado"), ("error", "error")],
                        db_index=True,
                        default="pending",
                        max_length=16,
                        verbose_name="estado",
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0, verbose_name="intentos")),
                ("last_error", models.TextField(blank=True, verbose_name="último error")),
                ("base_empresa", models.CharField(db_index=True, max_length=64, verbose_name="base empresa")),
                ("to_email", models.EmailField(max_length=254, verbose_name="destinatario")),
                ("subject", models.CharField(max_length=255, verbose_name="asunto")),
                ("body_text", models.TextField(verbose_name="cuerpo texto")),
                ("body_html", models.TextField(blank=True, verbose_name="cuerpo html")),
                ("payload_json", models.JSONField(blank=True, default=dict, verbose_name="payload")),
            ],
            options={
                "verbose_name": "cola mail e-com",
                "verbose_name_plural": "cola mails e-com",
                "ordering": ["created_at"],
            },
        ),
    ]
