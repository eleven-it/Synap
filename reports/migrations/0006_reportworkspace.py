from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0005_clientes_churn_axis_labels"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportWorkspace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Workspace", max_length=128, verbose_name="Name")),
                (
                    "items",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of report slugs included in the workspace.",
                        verbose_name="Reports",
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Created at")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
                (
                    "empresa",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_workspaces",
                        to="core.empresa",
                        verbose_name="Company",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_workspaces",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Owner",
                    ),
                ),
            ],
            options={
                "verbose_name": "Report workspace",
                "verbose_name_plural": "Report workspaces",
                "unique_together": {("owner", "empresa")},
            },
        ),
    ]
