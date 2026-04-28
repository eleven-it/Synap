# Generated manually for Synap IA learning / fine-tuning pipeline

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ia", "0004_register_moduleconfig_ia"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentLearningExample",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("auto_success", "Turno exitoso (automático)"),
                            ("user_positive", "Valoración positiva del usuario"),
                            ("user_correction", "Corrección del usuario"),
                            ("admin", "Curado por administrador"),
                        ],
                        default="auto_success",
                        max_length=32,
                        verbose_name="Origen",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendiente de revisión"),
                            ("approved", "Aprobado para entrenamiento"),
                            ("rejected", "Rechazado"),
                            ("exported", "Ya exportado a dataset externo"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Estado",
                    ),
                ),
                ("messages_payload", models.JSONField(default=list, help_text="Lista de {role, content} para export JSONL / fine-tuning.", verbose_name="Mensajes (formato chat)")),
                ("system_prompt_snapshot", models.TextField(blank=True, verbose_name="System prompt al capturar")),
                ("review_notes", models.TextField(blank=True, verbose_name="Notas de revisión")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="Revisado el")),
                ("metadata", models.JSONField(blank=True, default=dict, verbose_name="Metadata")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado")),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_examples",
                        to="ia.agentdefinition",
                        verbose_name="Agente",
                    ),
                ),
                (
                    "assistant_message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_examples_as_assistant",
                        to="ia.agentmessage",
                        verbose_name="Mensaje asistente",
                    ),
                ),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_examples",
                        to="ia.agentconversation",
                        verbose_name="Conversación",
                    ),
                ),
                (
                    "execution",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_example",
                        to="ia.agentexecution",
                        verbose_name="Ejecución origen",
                    ),
                ),
                (
                    "user_message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="learning_examples_as_user",
                        to="ia.agentmessage",
                        verbose_name="Mensaje usuario",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ia_learning_reviews",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Revisado por",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ejemplo de aprendizaje (IA)",
                "verbose_name_plural": "Ejemplos de aprendizaje (IA)",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="agentlearningexample",
            index=models.Index(fields=["agent", "status"], name="ia_learn_agent_status_idx"),
        ),
        migrations.AddIndex(
            model_name="agentlearningexample",
            index=models.Index(fields=["agent", "-created_at"], name="ia_learn_agent_created_idx"),
        ),
    ]
