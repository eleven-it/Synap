# Idempotencia para acciones sensibles (PATCH caso, asignar, enviar respuesta)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
        ("cases", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="IdempotencyRecord",
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
                    "action_key",
                    models.CharField(
                        db_index=True,
                        max_length=64,
                        verbose_name="Clave idempotencia (UUID)",
                    ),
                ),
                (
                    "status_code",
                    models.PositiveSmallIntegerField(verbose_name="Código HTTP guardado"),
                ),
                (
                    "response_payload",
                    models.JSONField(
                        default=dict,
                        verbose_name="Payload resumido de la respuesta",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="idempotency_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="idempotency_records",
                        to="cases.case",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registro idempotencia",
                "db_table": "support_idempotency_record",
            },
        ),
        migrations.AddIndex(
            model_name="idempotencyrecord",
            index=models.Index(
                fields=["case", "action_key", "actor"],
                name="support_idem_case_i_actor_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="idempotencyrecord",
            constraint=models.UniqueConstraint(
                fields=("case", "action_key", "actor"),
                name="support_idempotency_case_key_actor_uniq",
            ),
        ),
    ]
